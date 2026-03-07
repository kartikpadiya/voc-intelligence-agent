import os
import json
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from database import get_all_reviews, get_weekly_reviews

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Colors
PRIMARY    = colors.HexColor('#1a1a2e')
ACCENT     = colors.HexColor('#0f3460')
HIGHLIGHT  = colors.HexColor('#e94560')
SUCCESS    = colors.HexColor('#2ecc71')
WARNING    = colors.HexColor('#f39c12')
DANGER     = colors.HexColor('#e74c3c')
LIGHT      = colors.HexColor('#f8f9fa')
GRAY       = colors.HexColor('#6c757d')
WHITE      = colors.white


def get_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='CoverTitle', fontSize=32, textColor=WHITE,
        alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name='CoverSub', fontSize=13, textColor=colors.HexColor('#cccccc'),
        alignment=TA_CENTER, fontName='Helvetica', spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader', fontSize=15, textColor=WHITE,
        fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name='SubHeader', fontSize=12, textColor=ACCENT,
        fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=5
    ))
    styles.add(ParagraphStyle(
        name='Body2', fontSize=10, textColor=colors.HexColor('#333333'),
        fontName='Helvetica', spaceBefore=3, spaceAfter=3, leading=15
    ))
    styles.add(ParagraphStyle(
        name='Quote2', fontSize=10, textColor=colors.HexColor('#555555'),
        fontName='Helvetica-Oblique', spaceBefore=5, spaceAfter=5,
        leftIndent=20, rightIndent=20, leading=15
    ))
    styles.add(ParagraphStyle(
        name='AIText', fontSize=10, textColor=colors.HexColor('#1a1a2e'),
        fontName='Helvetica', spaceBefore=4, spaceAfter=4,
        leading=16, leftIndent=10
    ))
    return styles


def get_data(product_id):
    reviews = get_all_reviews(product_id)
    total = len(reviews)
    analyzed = [r for r in reviews if r.get("sentiment")]

    sentiment = {"Positive": 0, "Negative": 0, "Neutral": 0}
    for r in analyzed:
        s = r.get("sentiment", "Neutral")
        sentiment[s] = sentiment.get(s, 0) + 1

    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in reviews:
        rating = int(r.get("rating", 3))
        if rating in rating_dist:
            rating_dist[rating] += 1

    avg_rating = round(
        sum(r.get("rating", 0) for r in reviews) / total, 2
    ) if total > 0 else 0

    theme_data = {}
    for r in analyzed:
        themes = json.loads(r["themes"]) if r.get("themes") else []
        s = r.get("sentiment", "Neutral")
        for theme in themes:
            if theme not in theme_data:
                theme_data[theme] = {
                    "total": 0, "Positive": 0, "Negative": 0, "Neutral": 0
                }
            theme_data[theme]["total"] += 1
            theme_data[theme][s] += 1

    keywords = {
        "bluetooth": 0, "battery": 0, "sound quality": 0,
        "comfortable": 0, "anc": 0, "fit": 0, "return": 0,
        "disconnect": 0, "charging": 0, "mic": 0,
        "bass": 0, "volume": 0, "pairing": 0, "noise": 0
    }
    for r in reviews:
        text = (r.get("text", "") + " " + r.get("title", "")).lower()
        for kw in keywords:
            if kw in text:
                keywords[kw] += 1

    neg_reviews = [r for r in analyzed if r.get("sentiment") == "Negative"][:3]
    pos_reviews = [r for r in analyzed if r.get("sentiment") == "Positive"][:3]

    return {
        "total": total, "analyzed": len(analyzed),
        "sentiment": sentiment, "avg_rating": avg_rating,
        "rating_dist": rating_dist, "theme_data": theme_data,
        "keywords": keywords, "neg_reviews": neg_reviews,
        "pos_reviews": pos_reviews
    }


def get_ai_insights(product_name, data):
    print(f"Getting AI insights for {product_name}...")
    total = data["total"]
    analyzed = data["analyzed"]

    kw_summary = ""
    for kw, count in sorted(
        data["keywords"].items(), key=lambda x: -x[1]
    )[:10]:
        if count > 0:
            pct = round(count/total*100, 1)
            kw_summary += f"{kw}: {count}/{total} ({pct}%), "

    theme_summary = ""
    for theme, td in sorted(
        data["theme_data"].items(), key=lambda x: -x[1]["total"]
    ):
        pct = round(td["total"]/total*100, 1) if total > 0 else 0
        theme_summary += (
            f"{theme}: {td['total']} mentions ({pct}%), "
            f"Pos={td['Positive']}, Neg={td['Negative']}. "
        )

    pos_pct = round(
        data["sentiment"]["Positive"]/analyzed*100
    ) if analyzed > 0 else 0
    neg_pct = round(
        data["sentiment"]["Negative"]/analyzed*100
    ) if analyzed > 0 else 0

    prompt = (
        f"You are a senior VoC analyst. Analyze this data for {product_name}.\n\n"
        f"Total Reviews: {total}\n"
        f"Avg Rating: {data['avg_rating']}/5\n"
        f"Sentiment: {pos_pct}% Positive, {neg_pct}% Negative\n"
        f"Theme Data: {theme_summary}\n"
        f"Keyword Frequency: {kw_summary}\n\n"
        "Write a concise analysis with these sections. "
        "Use ONLY real numbers from data above:\n\n"
        "EXECUTIVE SUMMARY (3 sentences with actual numbers)\n\n"
        "TOP 3 BUGS/ISSUES (with frequency from data)\n\n"
        "TOP 3 STRENGTHS (with frequency from data)\n\n"
        "PRODUCT TEAM: Top 3 fixes needed\n\n"
        "MARKETING TEAM: Top 2 messaging recommendations\n\n"
        "SUPPORT TEAM: Top 2 guides to create\n\n"
        "Keep each section to 2-3 lines. Be specific with numbers."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=800
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"AI error: {e}")
        return "AI analysis unavailable."


def metric_card(label, value, bg_color):
    data = [[
        Paragraph(str(value), ParagraphStyle(
            'mv', fontSize=20, textColor=WHITE,
            fontName='Helvetica-Bold', alignment=TA_CENTER
        ))
    ], [
        Paragraph(label, ParagraphStyle(
            'ml', fontSize=8, textColor=colors.HexColor('#cccccc'),
            fontName='Helvetica', alignment=TA_CENTER
        ))
    ]]
    t = Table(data, colWidths=[1.4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    return t


def make_cover(story, styles, today):
    story.append(Spacer(1, 1.2*inch))
    cover = Table([[
        Paragraph("VOICE OF CUSTOMER", styles['CoverTitle'])
    ], [
        Paragraph("Intelligence Report", styles['CoverSub'])
    ], [
        Paragraph(
            f"Generated: {today}  |  Master Buds 1 vs Master Buds Max",
            styles['CoverSub']
        )
    ], [
        Paragraph(
            "Powered by AI Analysis + Real Customer Reviews",
            ParagraphStyle(
                'cs2', fontSize=11,
                textColor=colors.HexColor('#aaaaaa'),
                alignment=TA_CENTER, fontName='Helvetica-Oblique'
            )
        )
    ]], colWidths=[6.5*inch])

    cover.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 22),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 22),
        ('LEFTPADDING', (0, 0), (-1, -1), 30),
        ('RIGHTPADDING', (0, 0), (-1, -1), 30),
    ]))
    story.append(cover)
    story.append(PageBreak())


def make_product_page(story, styles, product_name, data, ai_insights):
    # Header
    header = Table([[
        Paragraph(f"  {product_name}", ParagraphStyle(
            'ph', fontSize=15, textColor=WHITE,
            fontName='Helvetica-Bold'
        ))
    ]], colWidths=[6.5*inch])
    header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), ACCENT),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
    ]))
    story.append(header)
    story.append(Spacer(1, 0.15*inch))

    # Metric Cards
    total = data["total"]
    analyzed = data["analyzed"]
    pos_pct = round(
        data["sentiment"]["Positive"]/analyzed*100
    ) if analyzed > 0 else 0
    neg_pct = round(
        data["sentiment"]["Negative"]/analyzed*100
    ) if analyzed > 0 else 0

    cards = Table([[
        metric_card("Total Reviews", total, PRIMARY),
        metric_card("Avg Rating", f"{data['avg_rating']}*", ACCENT),
        metric_card("Positive %", f"{pos_pct}%", SUCCESS),
        metric_card("Negative %", f"{neg_pct}%", DANGER),
    ]], colWidths=[1.5*inch]*4)
    cards.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(cards)
    story.append(Spacer(1, 0.2*inch))

    # AI Insights Section
    story.append(Paragraph("AI-Generated Insights", styles['SubHeader']))
    ai_box = Table([[
        Paragraph(ai_insights, styles['AIText'])
    ]], colWidths=[6.3*inch])
    ai_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f4ff')),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('BOX', (0, 0), (-1, -1), 1, ACCENT),
    ]))
    story.append(ai_box)
    story.append(Spacer(1, 0.2*inch))

    # Theme Table
    if data["theme_data"]:
        story.append(Paragraph("Theme Analysis", styles['SubHeader']))
        theme_rows = [[
            Paragraph("Theme", ParagraphStyle(
                'th', fontSize=10, fontName='Helvetica-Bold', textColor=WHITE
            )),
            Paragraph("Mentions", ParagraphStyle(
                'th', fontSize=10, fontName='Helvetica-Bold',
                textColor=WHITE, alignment=TA_CENTER
            )),
            Paragraph("Positive", ParagraphStyle(
                'th', fontSize=10, fontName='Helvetica-Bold',
                textColor=WHITE, alignment=TA_CENTER
            )),
            Paragraph("Negative", ParagraphStyle(
                'th', fontSize=10, fontName='Helvetica-Bold',
                textColor=WHITE, alignment=TA_CENTER
            )),
            Paragraph("Status", ParagraphStyle(
                'th', fontSize=10, fontName='Helvetica-Bold',
                textColor=WHITE, alignment=TA_CENTER
            ))
        ]]

        for theme, td in sorted(
            data["theme_data"].items(), key=lambda x: -x[1]["total"]
        ):
            pct = round(td["total"]/total*100, 1) if total > 0 else 0
            pos = td["Positive"]
            neg = td["Negative"]
            if neg > pos:
                status, sc = "PROBLEM", DANGER
            elif pos > neg * 2:
                status, sc = "STRENGTH", SUCCESS
            else:
                status, sc = "MIXED", WARNING

            theme_rows.append([
                Paragraph(theme, ParagraphStyle(
                    'tc', fontSize=9, fontName='Helvetica'
                )),
                Paragraph(f"{td['total']} ({pct}%)", ParagraphStyle(
                    'tc', fontSize=9, alignment=TA_CENTER
                )),
                Paragraph(str(pos), ParagraphStyle(
                    'tc', fontSize=9, textColor=SUCCESS,
                    alignment=TA_CENTER, fontName='Helvetica-Bold'
                )),
                Paragraph(str(neg), ParagraphStyle(
                    'tc', fontSize=9, textColor=DANGER,
                    alignment=TA_CENTER, fontName='Helvetica-Bold'
                )),
                Paragraph(status, ParagraphStyle(
                    'tc', fontSize=8, textColor=sc,
                    alignment=TA_CENTER, fontName='Helvetica-Bold'
                ))
            ])

        t = Table(
            theme_rows,
            colWidths=[2.2*inch, 1.2*inch, 1*inch, 1*inch, 1.1*inch]
        )
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT, WHITE]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.2*inch))

    # Issues Table
    story.append(Paragraph("Issue Frequency Analysis", styles['SubHeader']))
    issue_rows = [[
        Paragraph("Issue", ParagraphStyle(
            'ih', fontSize=10, fontName='Helvetica-Bold', textColor=WHITE
        )),
        Paragraph("Mentions", ParagraphStyle(
            'ih', fontSize=10, fontName='Helvetica-Bold',
            textColor=WHITE, alignment=TA_CENTER
        )),
        Paragraph("% of Reviews", ParagraphStyle(
            'ih', fontSize=10, fontName='Helvetica-Bold',
            textColor=WHITE, alignment=TA_CENTER
        )),
        Paragraph("Severity", ParagraphStyle(
            'ih', fontSize=10, fontName='Helvetica-Bold',
            textColor=WHITE, alignment=TA_CENTER
        ))
    ]]

    for kw, count in sorted(
        data["keywords"].items(), key=lambda x: -x[1]
    )[:10]:
        if count == 0:
            continue
        pct = round(count/total*100, 1)
        if pct > 20:
            sev, sc = "CRITICAL", DANGER
        elif pct > 10:
            sev, sc = "HIGH", WARNING
        elif pct > 5:
            sev, sc = "MEDIUM", colors.HexColor('#3498db')
        else:
            sev, sc = "LOW", SUCCESS

        issue_rows.append([
            Paragraph(kw.title(), ParagraphStyle(
                'ic', fontSize=9, fontName='Helvetica'
            )),
            Paragraph(str(count), ParagraphStyle(
                'ic', fontSize=9, alignment=TA_CENTER
            )),
            Paragraph(f"{pct}%", ParagraphStyle(
                'ic', fontSize=9, alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )),
            Paragraph(sev, ParagraphStyle(
                'ic', fontSize=8, textColor=sc,
                alignment=TA_CENTER, fontName='Helvetica-Bold'
            ))
        ])

    t2 = Table(
        issue_rows,
        colWidths=[2.5*inch, 1.3*inch, 1.3*inch, 1.4*inch]
    )
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HIGHLIGHT),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT, WHITE]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t2)
    story.append(Spacer(1, 0.2*inch))

    # Customer Quotes
    story.append(Paragraph("Customer Voice", styles['SubHeader']))
    if data["pos_reviews"]:
        story.append(Paragraph("TOP POSITIVE REVIEWS", ParagraphStyle(
            'pl', fontSize=9, fontName='Helvetica-Bold', textColor=SUCCESS
        )))
        for r in data["pos_reviews"]:
            story.append(Paragraph(
                f'"{r["title"]}" — {r["text"][:180]}...',
                styles['Quote2']
            ))
            story.append(Paragraph(
                f"Rating: {r['rating']}*",
                ParagraphStyle(
                    'rl', fontSize=8, textColor=SUCCESS, leftIndent=20
                )
            ))

    if data["neg_reviews"]:
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph("TOP NEGATIVE REVIEWS", ParagraphStyle(
            'nl', fontSize=9, fontName='Helvetica-Bold', textColor=DANGER
        )))
        for r in data["neg_reviews"]:
            story.append(Paragraph(
                f'"{r["title"]}" — {r["text"][:180]}...',
                styles['Quote2']
            ))
            story.append(Paragraph(
                f"Rating: {r['rating']}*",
                ParagraphStyle(
                    'rl', fontSize=8, textColor=DANGER, leftIndent=20
                )
            ))


def make_comparison_page(story, styles, data1, data2, ai_comparison):
    story.append(PageBreak())

    header = Table([[
        Paragraph("  HEAD TO HEAD COMPARISON", ParagraphStyle(
            'hh', fontSize=15, textColor=WHITE, fontName='Helvetica-Bold'
        ))
    ]], colWidths=[6.5*inch])
    header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HIGHLIGHT),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
    ]))
    story.append(header)
    story.append(Spacer(1, 0.2*inch))

    # AI Comparison
    story.append(Paragraph("AI Comparison Analysis", styles['SubHeader']))
    ai_box = Table([[
        Paragraph(ai_comparison, styles['AIText'])
    ]], colWidths=[6.3*inch])
    ai_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff5f5')),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('BOX', (0, 0), (-1, -1), 1, HIGHLIGHT),
    ]))
    story.append(ai_box)
    story.append(Spacer(1, 0.2*inch))

    # Comparison Table
    story.append(Paragraph("Feature by Feature", styles['SubHeader']))
    total1 = data1["total"]
    total2 = data2["total"]
    ana1 = data1["analyzed"]
    ana2 = data2["analyzed"]
    pos_pct1 = round(data1["sentiment"]["Positive"]/ana1*100) if ana1 > 0 else 0
    pos_pct2 = round(data2["sentiment"]["Positive"]/ana2*100) if ana2 > 0 else 0

    def winner_style(v1, v2):
        if v1 > v2:
            return "Buds 1 Wins", SUCCESS
        elif v2 > v1:
            return "Buds Max Wins", ACCENT
        return "Tie", GRAY

    rows = [[
        Paragraph("Metric", ParagraphStyle(
            'ch', fontSize=10, fontName='Helvetica-Bold', textColor=WHITE
        )),
        Paragraph("Master Buds 1", ParagraphStyle(
            'ch', fontSize=10, fontName='Helvetica-Bold',
            textColor=WHITE, alignment=TA_CENTER
        )),
        Paragraph("Master Buds Max", ParagraphStyle(
            'ch', fontSize=10, fontName='Helvetica-Bold',
            textColor=WHITE, alignment=TA_CENTER
        )),
        Paragraph("Winner", ParagraphStyle(
            'ch', fontSize=10, fontName='Helvetica-Bold',
            textColor=WHITE, alignment=TA_CENTER
        ))
    ]]

    metrics = [
        ("Avg Rating", data1["avg_rating"], data2["avg_rating"]),
        ("Positive Sentiment", pos_pct1, pos_pct2),
        ("Total Reviews", total1, total2),
    ]

    all_themes = set(
        list(data1["theme_data"].keys()) +
        list(data2["theme_data"].keys())
    )
    for theme in sorted(all_themes):
        td1 = data1["theme_data"].get(theme, {})
        td2 = data2["theme_data"].get(theme, {})
        metrics.append((
            theme,
            td1.get("Positive", 0),
            td2.get("Positive", 0)
        ))

    for metric, v1, v2 in metrics:
        w, wc = winner_style(v1, v2)
        rows.append([
            Paragraph(metric, ParagraphStyle(
                'cc', fontSize=9, fontName='Helvetica'
            )),
            Paragraph(str(v1), ParagraphStyle(
                'cc', fontSize=9, alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )),
            Paragraph(str(v2), ParagraphStyle(
                'cc', fontSize=9, alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )),
            Paragraph(w, ParagraphStyle(
                'cc', fontSize=9, textColor=wc,
                alignment=TA_CENTER, fontName='Helvetica-Bold'
            ))
        ])

    t = Table(
        rows,
        colWidths=[2.2*inch, 1.4*inch, 1.5*inch, 1.4*inch]
    )
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT, WHITE]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t)


def get_comparison_insights(data1, data2):
    print("Getting AI comparison insights...")
    total1 = data1["total"]
    total2 = data2["total"]
    ana1 = data1["analyzed"]
    ana2 = data2["analyzed"]
    pos_pct1 = round(data1["sentiment"]["Positive"]/ana1*100) if ana1 > 0 else 0
    pos_pct2 = round(data2["sentiment"]["Positive"]/ana2*100) if ana2 > 0 else 0

    prompt = (
        "Compare these two products as a VoC analyst:\n\n"
        f"Master Buds 1: {total1} reviews, avg {data1['avg_rating']}/5, "
        f"{pos_pct1}% positive\n"
        f"Themes: {json.dumps({k: v['total'] for k,v in data1['theme_data'].items()})}\n\n"
        f"Master Buds Max: {total2} reviews, avg {data2['avg_rating']}/5, "
        f"{pos_pct2}% positive\n"
        f"Themes: {json.dumps({k: v['total'] for k,v in data2['theme_data'].items()})}\n\n"
        "Write a concise comparison with:\n"
        "OVERALL WINNER (with reason and data)\n"
        "WHAT BUDS 1 DOES BETTER (2 points with data)\n"
        "WHAT BUDS MAX DOES BETTER (2 points with data)\n"
        "COMMON PROBLEMS ACROSS BOTH (2 points)\n"
        "TOP 3 COMBINED RECOMMENDATIONS\n\n"
        "Keep each section to 2 lines. Use real numbers only."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=600
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"AI error: {e}")
        return "AI comparison unavailable."


def generate_pdf():
    print("="*50)
    print("Generating Beautiful AI-Powered PDF Report...")
    print("="*50)

    os.makedirs("reports", exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"reports/voc_report_{datetime.now().strftime('%Y%m%d')}.pdf"

    doc = SimpleDocTemplate(
        filename, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )

    styles = get_styles()
    story = []

    make_cover(story, styles, today)

    print("Loading data...")
    data1 = get_data("master_buds_1")
    data2 = get_data("master_buds_max")

    ai1 = get_ai_insights("Master Buds 1 (EarFun)", data1)
    ai2 = get_ai_insights("Master Buds Max (Apple AirPods)", data2)
    ai_comp = get_comparison_insights(data1, data2)

    make_product_page(story, styles, "Master Buds 1 (EarFun)", data1, ai1)
    story.append(PageBreak())
    make_product_page(
        story, styles, "Master Buds Max (Apple AirPods)", data2, ai2
    )
    make_comparison_page(story, styles, data1, data2, ai_comp)

    doc.build(story)

    print(f"\nPDF saved: {filename}")
    print("Open from Finder: Desktop/voc-agent/reports/")
    return filename


if __name__ == "__main__":
    generate_pdf()
