import os
import json
import sqlite3
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from database import get_all_reviews, get_weekly_reviews, DB_PATH

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Colors
PRIMARY = HexColor("#0a0a0f")
ACCENT = HexColor("#e94560")
ACCENT2 = HexColor("#0f3460")
SUCCESS = HexColor("#2ecc71")
WARNING = HexColor("#f39c12")
DANGER = HexColor("#e74c3c")
LIGHT = HexColor("#f5f5f5")
DARK = HexColor("#1a1a2e")

THEMES = ["Sound Quality", "Battery Life", "Comfort/Fit", "App Experience",
          "Price/Value", "Delivery", "Build Quality", "ANC"]


# ─── DATA HELPERS ───

def get_products():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT product_id, product_name FROM reviews")
    products = cursor.fetchall()
    conn.close()
    return products


def get_stats(reviews):
    total = len(reviews)
    if not total:
        return {}
    avg = round(sum(r.get("rating", 0) for r in reviews) / total, 2)
    pos = sum(1 for r in reviews if r.get("sentiment") == "Positive")
    neg = sum(1 for r in reviews if r.get("sentiment") == "Negative")
    neu = total - pos - neg
    return {
        "total": total, "avg_rating": avg,
        "positive": pos, "positive_pct": f"{round(pos/total*100,1)}%",
        "negative": neg, "negative_pct": f"{round(neg/total*100,1)}%",
        "neutral": neu, "neutral_pct": f"{round(neu/total*100,1)}%",
    }


def get_theme_data(reviews):
    result = {}
    total = len(reviews)
    for theme in THEMES:
        result[theme] = {"Positive": 0, "Negative": 0, "Neutral": 0, "total": 0, "quotes": []}
    for r in reviews:
        themes = json.loads(r["themes"]) if r.get("themes") else []
        sentiment = r.get("sentiment", "Neutral")
        for theme in themes:
            if theme in result:
                result[theme][sentiment] += 1
                result[theme]["total"] += 1
                if len(result[theme]["quotes"]) < 2:
                    result[theme]["quotes"].append(f"[{r['rating']}★] {r['text'][:120]}")
    for theme in result:
        t = result[theme]["total"]
        result[theme]["pct"] = f"{round(t/total*100,1)}%" if total > 0 else "0%"
        pos = result[theme]["Positive"]
        neg = result[theme]["Negative"]
        if neg > pos:
            result[theme]["health"] = "PROBLEM AREA"
        elif pos > neg * 2:
            result[theme]["health"] = "STRENGTH"
        elif t == 0:
            result[theme]["health"] = "NO DATA"
        else:
            result[theme]["health"] = "MIXED"
    return result


def get_issues(reviews):
    keywords = {
        "Bluetooth Disconnects": ["disconnect", "bluetooth drop", "keeps disconnecting"],
        "Poor ANC": ["anc", "noise cancel", "no noise cancel"],
        "App Crashes": ["app crash", "app not working"],
        "Uncomfortable Fit": ["uncomfortable", "fall out", "hurts"],
        "Poor Battery": ["battery drain", "dies fast"],
        "Bad Mic": ["mic", "microphone", "call quality"],
        "Lag/Latency": ["lag", "latency", "delay"],
        "Pairing Issues": ["pairing", "won't connect"],
        "Bad Sound": ["bad sound", "tinny", "muffled"],
        "Charging Issues": ["charging", "won't charge"],
        "Poor Build": ["cheap", "broke", "flimsy"],
        "Touch Controls": ["touch control", "accidental tap"],
    }
    total = len(reviews)
    issues = {}
    for issue, kws in keywords.items():
        count = sum(1 for r in reviews
                    if any(kw in (r.get("text","") + r.get("title","")).lower() for kw in kws))
        if count > 0:
            pct = round(count/total*100, 1)
            severity = "CRITICAL" if pct > 20 else "HIGH" if pct > 10 else "MEDIUM" if pct > 5 else "LOW"
            issues[issue] = {"count": count, "pct": f"{pct}%", "severity": severity}
    return dict(sorted(issues.items(), key=lambda x: x[1]["count"], reverse=True))


def get_top_reviews(reviews, limit=3):
    pos = sorted([r for r in reviews if r.get("sentiment") == "Positive"],
                 key=lambda x: x.get("rating", 0), reverse=True)[:limit]
    neg = sorted([r for r in reviews if r.get("sentiment") == "Negative"],
                 key=lambda x: x.get("rating", 0))[:limit]
    return {
        "positive": [f"[{r['rating']}★] {r['title']}: {r['text'][:180]}" for r in pos],
        "negative": [f"[{r['rating']}★] {r['title']}: {r['text'][:180]}" for r in neg]
    }


def ask_groq(prompt, max_tokens=2000):
    import time
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "429" in str(e):
                print(f"    Rate limit - waiting 60s...")
                time.sleep(60)
            else:
                raise e
    return ""


# ─── GROQ ANALYSIS ───

def get_groq_insights(product_name, stats, themes, issues, top_reviews):
    prompt = f"""You are a VoC analyst for Noise. Analyze {product_name} data.

Stats: {json.dumps(stats)}
Themes: {json.dumps({t: {k:v for k,v in d.items() if k != 'quotes'} for t,d in themes.items()})}
Issues: {json.dumps(issues)}
Top Reviews: {json.dumps(top_reviews)}

Give EXACTLY (use real numbers only):

PRODUCT_ACTIONS:
1. [action with data evidence]
2. [action with data evidence]
3. [action with data evidence]
4. [action with data evidence]
5. [action with data evidence]

MARKETING_ACTIONS:
1. [action with data evidence]
2. [action with data evidence]
3. [action with data evidence]

SUPPORT_ACTIONS:
1. [action with data evidence]
2. [action with data evidence]
3. [action with data evidence]

TOP_RECOMMENDATIONS:
1. [recommendation | evidence | impact]
2. [recommendation | evidence | impact]
3. [recommendation | evidence | impact]
4. [recommendation | evidence | impact]
5. [recommendation | evidence | impact]

HEALTH_SUMMARY:
[2-3 sentences on product health with numbers]"""

    return ask_groq(prompt, 1500)


def get_competitor_insights(all_data):
    summaries = {}
    for pid, pname, reviews in all_data:
        analyzed = [r for r in reviews if r.get("sentiment")]
        if analyzed:
            summaries[pname] = {
                "stats": get_stats(analyzed),
                "themes": {t: {"health": d["health"], "pos": d["Positive"], "neg": d["Negative"]}
                          for t, d in get_theme_data(analyzed).items()},
                "top_issues": list(get_issues(analyzed).keys())[:5]
            }

    prompt = f"""Competitor analysis for Noise. Data:
{json.dumps(summaries, indent=2)}

Give EXACTLY:

WINNER_TABLE:
[Factor] | [Product1 score] | [Product2 score] | [Winner]
(do this for: Overall, Sound Quality, ANC, Battery, Comfort, App, Build, Price)

PRODUCT1_ADVANTAGES:
1. [advantage with data]
2. [advantage with data]
3. [advantage with data]

PRODUCT2_ADVANTAGES:
1. [advantage with data]
2. [advantage with data]
3. [advantage with data]

COMMON_WEAKNESSES:
1. [shared weakness]
2. [shared weakness]
3. [shared weakness]

GAPS_TO_WIN:
1. [opportunity with data]
2. [opportunity with data]
3. [opportunity with data]

CHURN_RISK:
[Which product and why - 2 sentences]"""

    return ask_groq(prompt, 1500)


# ─── PDF BUILDER ───

def build_pdf(global_data, weekly_data=None):
    os.makedirs("reports", exist_ok=True)
    filename = f"reports/voc_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            rightMargin=40, leftMargin=40,
                            topMargin=40, bottomMargin=40)

    styles = getSampleStyleSheet()
    elements = []

    # Custom styles
    title_style = ParagraphStyle("Title", fontSize=28, textColor=white,
                                  spaceAfter=6, alignment=TA_CENTER,
                                  fontName="Helvetica-Bold")
    h1 = ParagraphStyle("H1", fontSize=16, textColor=ACCENT,
                         spaceAfter=8, spaceBefore=16, fontName="Helvetica-Bold")
    h2 = ParagraphStyle("H2", fontSize=13, textColor=ACCENT2,
                         spaceAfter=6, spaceBefore=10, fontName="Helvetica-Bold")
    body = ParagraphStyle("Body", fontSize=9, textColor=black,
                           spaceAfter=4, leading=14)
    small = ParagraphStyle("Small", fontSize=8, textColor=HexColor("#555555"),
                            spaceAfter=3, leading=12, leftIndent=10)
    quote_style = ParagraphStyle("Quote", fontSize=8, textColor=HexColor("#333333"),
                                  spaceAfter=3, leading=12, leftIndent=15,
                                  borderPad=4)

    def add_cover():
        cover_data = [[Paragraph(
            f'<font color="white"><b>🎧 Voice of Customer Intelligence Report</b></font>',
            ParagraphStyle("Cover", fontSize=22, textColor=white,
                           alignment=TA_CENTER, fontName="Helvetica-Bold"))]]
        cover = Table(cover_data, colWidths=[515])
        cover.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), DARK),
            ("TOPPADDING", (0,0), (-1,-1), 30),
            ("BOTTOMPADDING", (0,0), (-1,-1), 30),
            ("LEFTPADDING", (0,0), (-1,-1), 20),
            ("RIGHTPADDING", (0,0), (-1,-1), 20),
            ("ROUNDEDCORNERS", [8]),
        ]))
        elements.append(cover)
        elements.append(Spacer(1, 10))

        today = datetime.now().strftime("%B %d, %Y")
        products_str = ", ".join([d["name"] for d in global_data])
        total = sum(d["stats"]["total"] for d in global_data if d.get("stats"))

        meta_data = [
            [Paragraph(f"<b>Date:</b> {today}", body),
             Paragraph(f"<b>Products:</b> {products_str}", body),
             Paragraph(f"<b>Total Reviews:</b> {total}", body)]
        ]
        meta = Table(meta_data, colWidths=[170, 230, 115])
        meta.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), LIGHT),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
        ]))
        elements.append(meta)
        elements.append(Spacer(1, 20))

    def add_stats_cards(stats, product_name):
        elements.append(Paragraph(f"📊 {product_name} — Health Snapshot", h1))

        avg = stats.get("avg_rating", 0)
        health_color = SUCCESS if avg >= 4 else WARNING if avg >= 3 else DANGER

        cards = [
            [Paragraph(f'<b>{stats.get("total", 0)}</b>', ParagraphStyle("Card", fontSize=22, textColor=ACCENT, alignment=TA_CENTER, fontName="Helvetica-Bold")),
             Paragraph(f'<b>{stats.get("avg_rating", 0)}/5</b>', ParagraphStyle("Card", fontSize=22, textColor=health_color, alignment=TA_CENTER, fontName="Helvetica-Bold")),
             Paragraph(f'<b>{stats.get("positive_pct", "0%")}</b>', ParagraphStyle("Card", fontSize=22, textColor=SUCCESS, alignment=TA_CENTER, fontName="Helvetica-Bold")),
             Paragraph(f'<b>{stats.get("negative_pct", "0%")}</b>', ParagraphStyle("Card", fontSize=22, textColor=DANGER, alignment=TA_CENTER, fontName="Helvetica-Bold"))],
            [Paragraph("Total Reviews", ParagraphStyle("CardLabel", fontSize=8, textColor=HexColor("#666"), alignment=TA_CENTER)),
             Paragraph("Avg Rating", ParagraphStyle("CardLabel", fontSize=8, textColor=HexColor("#666"), alignment=TA_CENTER)),
             Paragraph("Positive", ParagraphStyle("CardLabel", fontSize=8, textColor=HexColor("#666"), alignment=TA_CENTER)),
             Paragraph("Negative", ParagraphStyle("CardLabel", fontSize=8, textColor=HexColor("#666"), alignment=TA_CENTER))]
        ]
        t = Table(cards, colWidths=[128, 128, 128, 128])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), LIGHT),
            ("TOPPADDING", (0,0), (-1,-1), 12),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, HexColor("#dddddd")),
            ("ROUNDEDCORNERS", [6]),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

    def add_theme_table(themes):
        elements.append(Paragraph("🏷️ Theme-Wise Analysis", h2))

        header = [
            Paragraph("<b>Theme</b>", ParagraphStyle("TH", fontSize=8, textColor=white, fontName="Helvetica-Bold")),
            Paragraph("<b>✅ Pos</b>", ParagraphStyle("TH", fontSize=8, textColor=white, fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph("<b>❌ Neg</b>", ParagraphStyle("TH", fontSize=8, textColor=white, fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph("<b>➖ Neu</b>", ParagraphStyle("TH", fontSize=8, textColor=white, fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph("<b>% Reviews</b>", ParagraphStyle("TH", fontSize=8, textColor=white, fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph("<b>Health</b>", ParagraphStyle("TH", fontSize=8, textColor=white, fontName="Helvetica-Bold", alignment=TA_CENTER)),
        ]
        rows = [header]
        row_colors = []

        for i, (theme, data) in enumerate(themes.items()):
            health = data["health"]
            health_color = SUCCESS if health == "STRENGTH" else DANGER if health == "PROBLEM AREA" else WARNING if health == "MIXED" else HexColor("#aaaaaa")
            health_symbol = "🟢 STRENGTH" if health == "STRENGTH" else "🔴 PROBLEM" if health == "PROBLEM AREA" else "🟡 MIXED" if health == "MIXED" else "⚪ NO DATA"

            row = [
                Paragraph(theme, ParagraphStyle("TD", fontSize=8)),
                Paragraph(str(data["Positive"]), ParagraphStyle("TD", fontSize=8, alignment=TA_CENTER, textColor=HexColor("#27ae60"))),
                Paragraph(str(data["Negative"]), ParagraphStyle("TD", fontSize=8, alignment=TA_CENTER, textColor=DANGER)),
                Paragraph(str(data["Neutral"]), ParagraphStyle("TD", fontSize=8, alignment=TA_CENTER)),
                Paragraph(data["pct"], ParagraphStyle("TD", fontSize=8, alignment=TA_CENTER)),
                Paragraph(health_symbol, ParagraphStyle("TD", fontSize=7, alignment=TA_CENTER)),
            ]
            rows.append(row)
            row_colors.append(HexColor("#f9f9f9") if i % 2 == 0 else white)

        t = Table(rows, colWidths=[130, 55, 55, 55, 70, 150])
        style = [
            ("BACKGROUND", (0,0), (-1,0), DARK),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("GRID", (0,0), (-1,-1), 0.3, HexColor("#dddddd")),
        ]
        for i, color in enumerate(row_colors):
            style.append(("BACKGROUND", (0, i+1), (-1, i+1), color))
        t.setStyle(TableStyle(style))
        elements.append(t)
        elements.append(Spacer(1, 8))

        # Quotes per theme
        elements.append(Paragraph("💬 Theme Quotes", h2))
        for theme, data in themes.items():
            if data["quotes"]:
                elements.append(Paragraph(f"<b>{theme}:</b>", small))
                elements.append(Paragraph(f"<i>\"{data['quotes'][0]}\"</i>", quote_style))

        elements.append(Spacer(1, 8))

    def add_issues_table(issues):
        elements.append(Paragraph("🔴 Top Issues — Severity Ranked", h2))

        header = [
            Paragraph("<b>Issue</b>", ParagraphStyle("TH", fontSize=8, textColor=white, fontName="Helvetica-Bold")),
            Paragraph("<b>Count</b>", ParagraphStyle("TH", fontSize=8, textColor=white, fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph("<b>%</b>", ParagraphStyle("TH", fontSize=8, textColor=white, fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph("<b>Severity</b>", ParagraphStyle("TH", fontSize=8, textColor=white, fontName="Helvetica-Bold", alignment=TA_CENTER)),
        ]
        rows = [header]
        for issue, data in issues.items():
            sev = data["severity"]
            sev_color = DANGER if sev == "CRITICAL" else WARNING if sev == "HIGH" else HexColor("#f1c40f") if sev == "MEDIUM" else SUCCESS
            rows.append([
                Paragraph(issue, ParagraphStyle("TD", fontSize=8)),
                Paragraph(str(data["count"]), ParagraphStyle("TD", fontSize=8, alignment=TA_CENTER)),
                Paragraph(data["pct"], ParagraphStyle("TD", fontSize=8, alignment=TA_CENTER)),
                Paragraph(sev, ParagraphStyle("TD", fontSize=8, alignment=TA_CENTER, textColor=sev_color, fontName="Helvetica-Bold")),
            ])

        t = Table(rows, colWidths=[230, 60, 60, 165])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), DARK),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("GRID", (0,0), (-1,-1), 0.3, HexColor("#dddddd")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [LIGHT, white]),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 8))

    def add_reviews(top_reviews):
        elements.append(Paragraph("⭐ Top Customer Reviews", h2))

        elements.append(Paragraph("✅ Best Reviews:", small))
        for r in top_reviews["positive"]:
            elements.append(Paragraph(f"<i>\"{r}\"</i>", quote_style))

        elements.append(Spacer(1, 6))
        elements.append(Paragraph("❌ Worst Reviews:", small))
        for r in top_reviews["negative"]:
            elements.append(Paragraph(f"<i>\"{r}\"</i>", quote_style))
        elements.append(Spacer(1, 8))

    def add_actions(insights, product_name):
        sections = {
            "PRODUCT_ACTIONS": ("🛠️ Product Team Actions", ACCENT2),
            "MARKETING_ACTIONS": ("📣 Marketing Team Actions", HexColor("#8e44ad")),
            "SUPPORT_ACTIONS": ("🎧 Support Team Actions", HexColor("#16a085")),
            "TOP_RECOMMENDATIONS": ("🏆 Top 5 Recommendations", ACCENT),
            "HEALTH_SUMMARY": ("💡 Health Summary", DARK),
        }

        current_section = None
        lines = insights.split("\n")
        action_items = {}
        current_key = None

        for line in lines:
            line = line.strip()
            for key in sections:
                if line.startswith(key + ":"):
                    current_key = key
                    action_items[current_key] = []
                    break
            else:
                if current_key and line and not line.endswith(":"):
                    action_items[current_key] = action_items.get(current_key, []) + [line]

        for key, (title, color) in sections.items():
            if key in action_items and action_items[key]:
                elements.append(Paragraph(title, ParagraphStyle("H2c", fontSize=12,
                    textColor=color, spaceAfter=6, spaceBefore=10, fontName="Helvetica-Bold")))
                for item in action_items[key]:
                    if item.strip():
                        elements.append(Paragraph(f"• {item}", body))
                elements.append(Spacer(1, 6))

    def add_competitor(competitor_insights, names):
        elements.append(HRFlowable(width="100%", thickness=2, color=ACCENT))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("🏆 Competitor Gap Analysis", h1))

        lines = competitor_insights.split("\n")
        current_section = None
        table_rows = []
        in_table = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("WINNER_TABLE:"):
                elements.append(Paragraph("📊 Head-to-Head Comparison", h2))
                in_table = True
                table_rows = []
            elif any(line.startswith(s) for s in ["PRODUCT1_ADVANTAGES:", "PRODUCT2_ADVANTAGES:",
                                                    "COMMON_WEAKNESSES:", "GAPS_TO_WIN:", "CHURN_RISK:"]):
                if in_table and table_rows:
                    # Render table
                    header = [Paragraph("<b>Factor</b>", ParagraphStyle("TH", fontSize=8, textColor=white, fontName="Helvetica-Bold"))]
                    for n in names:
                        header.append(Paragraph(f"<b>{n[:15]}</b>", ParagraphStyle("TH", fontSize=7, textColor=white, fontName="Helvetica-Bold", alignment=TA_CENTER)))
                    header.append(Paragraph("<b>Winner</b>", ParagraphStyle("TH", fontSize=8, textColor=white, fontName="Helvetica-Bold", alignment=TA_CENTER)))

                    t_rows = [header]
                    for tr in table_rows:
                        parts = [p.strip() for p in tr.split("|")]
                        if len(parts) >= 2:
                            row = [Paragraph(parts[0], ParagraphStyle("TD", fontSize=8))]
                            for p in parts[1:]:
                                row.append(Paragraph(p, ParagraphStyle("TD", fontSize=7, alignment=TA_CENTER)))
                            while len(row) < len(header):
                                row.append(Paragraph("-", ParagraphStyle("TD", fontSize=7, alignment=TA_CENTER)))
                            t_rows.append(row[:len(header)])

                    col_w = [150] + [120 // len(names)] * len(names) + [80]
                    ct = Table(t_rows, colWidths=col_w)
                    ct.setStyle(TableStyle([
                        ("BACKGROUND", (0,0), (-1,0), DARK),
                        ("TOPPADDING", (0,0), (-1,-1), 5),
                        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                        ("LEFTPADDING", (0,0), (-1,-1), 5),
                        ("GRID", (0,0), (-1,-1), 0.3, HexColor("#dddddd")),
                        ("ROWBACKGROUNDS", (0,1), (-1,-1), [LIGHT, white]),
                    ]))
                    elements.append(ct)
                    elements.append(Spacer(1, 8))
                    in_table = False

                section_titles = {
                    "PRODUCT1_ADVANTAGES:": f"💪 {names[0] if names else 'Product 1'} Leads",
                    "PRODUCT2_ADVANTAGES:": f"💪 {names[1] if len(names)>1 else 'Product 2'} Leads",
                    "COMMON_WEAKNESSES:": "⚠️ Common Weaknesses",
                    "GAPS_TO_WIN:": "🚀 Gaps To Win",
                    "CHURN_RISK:": "⚡ Churn Risk",
                }
                for k, v in section_titles.items():
                    if line.startswith(k):
                        elements.append(Paragraph(v, h2))
                        break
                current_section = line

            elif in_table and "|" in line:
                table_rows.append(line)
            elif line and not line.endswith(":"):
                if line.startswith(("1.", "2.", "3.", "4.", "5.")):
                    elements.append(Paragraph(f"• {line[2:].strip()}", body))
                else:
                    elements.append(Paragraph(line, body))

    # ─── BUILD PDF ───

    add_cover()

    product_names = []

    for prod_data in global_data:
        pname = prod_data["name"]
        product_names.append(pname)
        stats = prod_data["stats"]
        themes = prod_data["themes"]
        issues = prod_data["issues"]
        top_reviews = prod_data["top_reviews"]
        insights = prod_data["insights"]

        elements.append(HRFlowable(width="100%", thickness=2, color=ACCENT))
        elements.append(Spacer(1, 10))

        add_stats_cards(stats, pname)
        add_theme_table(themes)
        add_issues_table(issues)
        add_reviews(top_reviews)
        add_actions(insights, pname)

    # Competitor section
    if len(global_data) >= 2 and "competitor" in global_data[0]:
        add_competitor(global_data[0]["competitor"], product_names)

    # Weekly section
    if weekly_data:
        elements.append(HRFlowable(width="100%", thickness=2, color=SUCCESS))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"📅 Weekly Delta Report — {weekly_data['week']}", h1))
        elements.append(Paragraph(f"New Reviews This Week: {weekly_data['stats'].get('total', 0)}", body))
        elements.append(Spacer(1, 8))

        add_stats_cards(weekly_data["stats"], "This Week")
        add_theme_table(weekly_data["themes"])
        add_issues_table(weekly_data["issues"])
        add_reviews(weekly_data["top_reviews"])
        add_actions(weekly_data["insights"], "Weekly")

    doc.build(elements)
    print(f"\n✅ PDF saved: {filename}")
    return filename


# ─── MAIN ───

def generate_full_pdf():
    print("=" * 55)
    print("VocBot — Generating PDF Report via Groq + ReportLab")
    print("=" * 55)

    products = get_products()
    if not products:
        print("No products in DB!")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    global_data = []
    all_products_for_competitor = []

    for product_id, product_name in products:
        reviews = get_all_reviews(product_id)
        analyzed = [r for r in reviews if r.get("sentiment")]
        if not analyzed:
            print(f"  {product_name}: No analyzed reviews — skipping")
            continue

        print(f"\n📦 Processing {product_name} ({len(analyzed)} reviews)...")

        stats = get_stats(analyzed)
        themes = get_theme_data(analyzed)
        issues = get_issues(analyzed)
        top_reviews = get_top_reviews(analyzed)

        print(f"  Getting Groq insights...")
        insights = get_groq_insights(product_name, stats, themes, issues, top_reviews)

        prod_data = {
            "name": product_name,
            "stats": stats,
            "themes": themes,
            "issues": issues,
            "top_reviews": top_reviews,
            "insights": insights,
        }
        global_data.append(prod_data)
        all_products_for_competitor.append((product_id, product_name, analyzed))

    # Competitor analysis
    if len(all_products_for_competitor) >= 2:
        print("\n🏆 Getting competitor analysis...")
        competitor_insights = get_competitor_insights(all_products_for_competitor)
        if global_data:
            global_data[0]["competitor"] = competitor_insights

    # Weekly data
    weekly_data = None
    weekly_reviews = get_weekly_reviews()
    weekly_analyzed = [r for r in weekly_reviews if r.get("sentiment")] if weekly_reviews else []

    if weekly_analyzed:
        print(f"\n📅 Processing weekly delta ({len(weekly_analyzed)} reviews)...")
        w_stats = get_stats(weekly_analyzed)
        w_themes = get_theme_data(weekly_analyzed)
        w_issues = get_issues(weekly_analyzed)
        w_top_reviews = get_top_reviews(weekly_analyzed)
        w_insights = get_groq_insights("Weekly Delta", w_stats, w_themes, w_issues, w_top_reviews)

        weekly_data = {
            "week": datetime.now().strftime("%Y-W%U"),
            "stats": w_stats,
            "themes": w_themes,
            "issues": w_issues,
            "top_reviews": w_top_reviews,
            "insights": w_insights,
        }

    print("\n📄 Building PDF...")
    filename = build_pdf(global_data, weekly_data)
    return filename


if __name__ == "__main__":
    generate_full_pdf()
