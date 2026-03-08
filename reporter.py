import os
import json
import sqlite3
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from database import get_all_reviews, get_weekly_reviews, DB_PATH

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

THEMES = [
    "Sound Quality", "Battery Life", "Comfort/Fit",
    "App Experience", "Price/Value", "Delivery",
    "Build Quality", "ANC"
]


# ─────────────────────────────────────────
# DATA HELPERS
# ─────────────────────────────────────────

def get_products_from_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT product_id, product_name FROM reviews")
    products = cursor.fetchall()
    conn.close()
    return products


def get_theme_tagging(reviews):
    """Theme wise Positive/Negative/Neutral counts"""
    result = {}
    total = len(reviews)
    for theme in THEMES:
        result[theme] = {"Positive": 0, "Negative": 0, "Neutral": 0, "total": 0, "top_reviews": []}

    for r in reviews:
        themes = json.loads(r["themes"]) if r.get("themes") else []
        sentiment = r.get("sentiment", "Neutral")
        for theme in themes:
            if theme in result:
                result[theme][sentiment] += 1
                result[theme]["total"] += 1
                if len(result[theme]["top_reviews"]) < 3:
                    result[theme]["top_reviews"].append(
                        f"[{sentiment}][{r['rating']}★] {r['title']}: {r['text'][:150]}"
                    )

    # Add percentages and health
    for theme in result:
        t = result[theme]["total"]
        if t > 0:
            result[theme]["pct_of_reviews"] = f"{round(t/total*100,1)}%"
            pos = result[theme]["Positive"]
            neg = result[theme]["Negative"]
            if neg > pos:
                result[theme]["health"] = "🔴 PROBLEM AREA"
            elif pos > neg * 2:
                result[theme]["health"] = "🟢 STRENGTH"
            else:
                result[theme]["health"] = "🟡 MIXED"
        else:
            result[theme]["pct_of_reviews"] = "0%"
            result[theme]["health"] = "⚪ NO DATA"

    return result


def get_top_issues(reviews):
    """Top issues with severity"""
    keywords = {
        "disconnects/bluetooth drops": ["disconnect", "bluetooth drop", "keeps disconnecting"],
        "poor ANC": ["anc", "noise cancel", "no noise cancel"],
        "app crashes": ["app crash", "app not working", "app issue"],
        "uncomfortable fit": ["uncomfortable", "fall out", "hurts", "pain"],
        "poor battery": ["battery drain", "battery life", "dies fast"],
        "bad mic quality": ["mic", "microphone", "call quality"],
        "lag/latency": ["lag", "latency", "delay"],
        "pairing issues": ["pairing", "won't connect", "connect issue"],
        "bad sound quality": ["sound quality", "bad sound", "tinny", "muffled"],
        "charging issues": ["charging", "won't charge", "charge issue"],
        "build quality": ["cheap", "broke", "plastic", "flimsy"],
        "touch controls": ["touch", "controls not working", "accidental"],
    }
    total = len(reviews)
    issues = {}
    for issue, kws in keywords.items():
        count = 0
        samples = []
        for r in reviews:
            text = (r.get("text","") + " " + r.get("title","")).lower()
            if any(kw in text for kw in kws):
                count += 1
                if len(samples) < 2:
                    samples.append(f"[{r['rating']}★] {r['text'][:120]}")
        if count > 0:
            pct = round(count/total*100, 1)
            severity = "🔴 CRITICAL" if pct > 20 else "🟠 HIGH" if pct > 10 else "🟡 MEDIUM" if pct > 5 else "🟢 LOW"
            issues[issue] = {
                "count": count,
                "percentage": f"{pct}%",
                "severity": severity,
                "sample_reviews": samples
            }
    return dict(sorted(issues.items(), key=lambda x: x[1]["count"], reverse=True))


def get_top_reviews(reviews, limit=5):
    """Top positive and negative reviews"""
    pos = sorted([r for r in reviews if r.get("sentiment") == "Positive"],
                 key=lambda x: x.get("rating", 0), reverse=True)[:limit]
    neg = sorted([r for r in reviews if r.get("sentiment") == "Negative"],
                 key=lambda x: x.get("rating", 0))[:limit]
    return {
        "top_positive": [f"[{r['rating']}★] {r['title']}: {r['text'][:200]}" for r in pos],
        "top_negative": [f"[{r['rating']}★] {r['title']}: {r['text'][:200]}" for r in neg]
    }


def get_rating_sentiment(reviews):
    total = len(reviews)
    if not total:
        return {}
    avg = round(sum(r.get("rating", 0) for r in reviews) / total, 2)
    pos = sum(1 for r in reviews if r.get("sentiment") == "Positive")
    neg = sum(1 for r in reviews if r.get("sentiment") == "Negative")
    neu = total - pos - neg
    return {
        "total_reviews": total,
        "avg_rating": avg,
        "positive_pct": f"{round(pos/total*100,1)}%",
        "negative_pct": f"{round(neg/total*100,1)}%",
        "neutral_pct": f"{round(neu/total*100,1)}%",
    }


# ─────────────────────────────────────────
# SINGLE PRODUCT REPORT
# ─────────────────────────────────────────

def generate_single_product_report(product_id, product_name, reviews, today):
    print(f"  Generating report for {product_name}...")
    analyzed = [r for r in reviews if r.get("sentiment")]
    if not analyzed:
        return f"# {product_name}\nNo analyzed reviews."

    themes = get_theme_tagging(analyzed)
    issues = get_top_issues(analyzed)
    top_reviews = get_top_reviews(analyzed)
    stats = get_rating_sentiment(analyzed)

    prompt = (
        f"You are a senior VoC Analyst at Noise.\n"
        f"Generate a structured report for {product_name}.\n"
        f"Use ONLY the data provided. No hallucinations.\n\n"
        f"=== STATS ===\n{json.dumps(stats, indent=2)}\n\n"
        f"=== THEME TAGGING (Pos/Neg/Neutral per theme) ===\n{json.dumps(themes, indent=2)}\n\n"
        f"=== TOP ISSUES WITH SEVERITY ===\n{json.dumps(issues, indent=2)}\n\n"
        f"=== TOP REVIEWS ===\n{json.dumps(top_reviews, indent=2)}\n\n"
        f"Generate report with EXACTLY this structure:\n\n"
        f"# {product_name} — VoC Intelligence Report\n"
        f"**Date:** {today}\n\n"
        f"## 📊 Product Health Snapshot\n"
        f"Avg Rating, Sentiment split, 1-line health summary.\n\n"
        f"## 🏷️ Theme-Wise Analysis\n"
        f"For ALL 8 themes show:\n"
        f"- Positive / Negative / Neutral counts\n"
        f"- Health status (STRENGTH / PROBLEM AREA / MIXED)\n"
        f"- 1 top customer quote\n\n"
        f"## ⭐ Top Customer Reviews\n"
        f"Top 3 positive and top 3 negative reviews verbatim.\n\n"
        f"## 🔴 Top Issues — Severity Ranked\n"
        f"List ALL issues from data ranked by severity.\n"
        f"Format: Issue | Count | % | Severity | Sample Quote\n\n"
        f"## 🛠️ Product Team Actions\n"
        f"Top 5 specific actions with severity and data evidence.\n\n"
        f"## 📣 Marketing Team Actions\n"
        f"What to highlight, what to stop claiming — with data.\n\n"
        f"## 🎧 Support Team Actions\n"
        f"Top complaints to address, FAQs to create, guides needed.\n\n"
        f"## 🏆 Top 5 Recommendations\n"
        f"| # | What | Why (Data) | Impact |\n"
        f"|---|------|-----------|--------|\n"
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=3000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error: {e}")
        return None


# ─────────────────────────────────────────
# COMPETITOR GAP ANALYSIS
# ─────────────────────────────────────────

def generate_competitor_analysis(all_products_data, today):
    print("  Generating Competitor Gap Analysis...")

    summaries = {}
    for pid, pname, reviews in all_products_data:
        analyzed = [r for r in reviews if r.get("sentiment")]
        if not analyzed:
            continue
        summaries[pname] = {
            "stats": get_rating_sentiment(analyzed),
            "themes": {
                t: {
                    "Positive": d["Positive"],
                    "Negative": d["Negative"],
                    "health": d["health"]
                }
                for t, d in get_theme_tagging(analyzed).items()
            },
            "top_issues": {
                k: {"count": v["count"], "severity": v["severity"]}
                for k, v in list(get_top_issues(analyzed).items())[:8]
            },
            "top_positive": get_top_reviews(analyzed)["top_positive"][:2],
            "top_negative": get_top_reviews(analyzed)["top_negative"][:2],
        }

    if len(summaries) < 2:
        return "# Competitor Analysis\nNeed at least 2 products."

    names = list(summaries.keys())

    prompt = (
        f"You are a competitive intelligence analyst at Noise.\n"
        f"Compare products and find gaps using ONLY provided data.\n\n"
        f"=== PRODUCT DATA ===\n{json.dumps(summaries, indent=2)}\n\n"
        f"Generate EXACTLY:\n\n"
        f"# 🏆 Competitor Gap Analysis\n"
        f"**Date:** {today}\n\n"
        f"## 📊 Head-to-Head Scorecard\n"
        f"| Factor | " + " | ".join(names) + " | Winner |\n"
        f"|--------|" + "--------|" * len(names) + "--------|\n"
        f"Fill for: Avg Rating, Positive%, Negative%, "
        f"Sound Quality, ANC, Battery Life, Comfort/Fit, "
        f"App Experience, Build Quality, Price/Value\n\n"
        f"## 💪 Where Each Product Leads\n"
        f"For each product: top 3 advantages with data.\n\n"
        f"## ⚠️ Common Weaknesses (All Products)\n"
        f"Issues affecting all products — industry-wide problems.\n\n"
        f"## 🎯 Top Issues Comparison\n"
        f"| Issue | " + " | ".join(names) + " |\n"
        f"|-------|" + "-------|" * len(names) + "\n"
        f"Compare top issues across products.\n\n"
        f"## 🚀 Gaps To Close (Opportunities for Noise)\n"
        f"Top 3 areas where improvement beats competition.\n\n"
        f"## 📣 Positioning Recommendations\n"
        f"How to position each product based on actual data.\n\n"
        f"## ⚡ Customer Switching Risk\n"
        f"Which product is at highest churn risk and why.\n\n"
        f"Use only data provided."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error: {e}")
        return None


# ─────────────────────────────────────────
# GLOBAL REPORT
# ─────────────────────────────────────────

def generate_global_report():
    print("=" * 55)
    print("Generating Global VoC Intelligence Report...")
    print("=" * 55)

    products = get_products_from_db()
    if not products:
        print("No products in DB!")
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    all_products_data = []

    for product_id, product_name in products:
        reviews = get_all_reviews(product_id)
        all_products_data.append((product_id, product_name, reviews))
        print(f"  {product_name}: {len(reviews)} reviews")

    product_reports = []
    for pid, pname, reviews in all_products_data:
        report = generate_single_product_report(pid, pname, reviews, today)
        if report:
            product_reports.append(report)

    competitor = generate_competitor_analysis(all_products_data, today)

    total_reviews = sum(len(r[2]) for r in all_products_data)
    final_report = (
        f"# 🎧 Voice of Customer Intelligence Report\n"
        f"**Generated:** {today} | "
        f"**Products:** {', '.join([p[1] for p in products])} | "
        f"**Total Reviews:** {total_reviews}\n\n"
        f"---\n\n"
        + "\n\n---\n\n".join(product_reports)
        + "\n\n---\n\n"
        + (competitor or "")
    )

    os.makedirs("reports", exist_ok=True)
    filename = f"reports/global_report_{datetime.now().strftime('%Y%m%d')}.md"
    with open(filename, "w") as f:
        f.write(final_report)

    print(f"\n✅ Global report saved: {filename}")
    return final_report


# ─────────────────────────────────────────
# WEEKLY DELTA REPORT
# ─────────────────────────────────────────

def generate_weekly_report():
    print("=" * 55)
    print("Generating Weekly Delta Report...")
    print("=" * 55)

    weekly_reviews = get_weekly_reviews()
    if not weekly_reviews:
        print("No new reviews this week!")
        return None

    analyzed = [r for r in weekly_reviews if r.get("sentiment")]
    if not analyzed:
        print("Weekly reviews not analyzed yet!")
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    week = datetime.now().strftime("%Y-W%U")

    # This week data
    themes = get_theme_tagging(analyzed)
    issues = get_top_issues(analyzed)
    top_reviews = get_top_reviews(analyzed)
    stats = get_rating_sentiment(analyzed)

    # Previous period for comparison
    all_old = []
    for pid, pname in get_products_from_db():
        reviews = get_all_reviews(pid)
        all_old.extend([r for r in reviews
                       if r.get("week_added") == "2025-W01"
                       and r.get("sentiment")])

    old_stats = get_rating_sentiment(all_old) if all_old else {}
    old_themes = {
        t: {"Positive": d["Positive"], "Negative": d["Negative"], "health": d["health"]}
        for t, d in get_theme_tagging(all_old).items()
    } if all_old else {}
    old_issues = {
        k: {"count": v["count"], "severity": v["severity"]}
        for k, v in list(get_top_issues(all_old).items())[:8]
    } if all_old else {}

    prompt = (
        f"You are a senior VoC Analyst at Noise.\n"
        f"Generate Weekly Delta Report for week {week}.\n"
        f"Show what CHANGED vs previous period. Use ONLY real numbers.\n\n"
        f"=== THIS WEEK ({len(analyzed)} new reviews) ===\n"
        f"Stats: {json.dumps(stats, indent=2)}\n"
        f"Themes: {json.dumps(themes, indent=2)}\n"
        f"Issues: {json.dumps(issues, indent=2)}\n"
        f"Top Reviews: {json.dumps(top_reviews, indent=2)}\n\n"
        f"=== PREVIOUS PERIOD (baseline) ===\n"
        f"Stats: {json.dumps(old_stats, indent=2)}\n"
        f"Themes: {json.dumps(old_themes, indent=2)}\n"
        f"Issues: {json.dumps(old_issues, indent=2)}\n\n"
        f"Generate EXACTLY:\n\n"
        f"# 📅 Weekly Delta Report — {week}\n"
        f"**Date:** {today} | **New Reviews:** {len(analyzed)}\n\n"
        f"## 📊 Week At A Glance\n"
        f"| Metric | This Week | Previous | Change |\n"
        f"|--------|-----------|----------|--------|\n"
        f"Fill: Avg Rating, Positive%, Negative%, Top Theme, Review Count\n\n"
        f"## 🏷️ Theme-Wise This Week\n"
        f"For ALL 8 themes:\n"
        f"- Positive / Negative / Neutral counts\n"
        f"- Health vs previous (better/worse/same)\n"
        f"- 1 top customer quote\n\n"
        f"## ⭐ Top Reviews This Week\n"
        f"Top 3 positive and top 3 negative verbatim.\n\n"
        f"## 🔴 Top Issues This Week — Severity Ranked\n"
        f"Issue | Count | % | Severity | Change vs Last Week\n\n"
        f"## 📈 Complaint Spikes (New or Worsened)\n"
        f"Issues that increased vs previous period with data.\n\n"
        f"## 📉 Improvements This Week\n"
        f"Issues that decreased or themes that improved.\n\n"
        f"## 🛠️ Urgent Product Team Actions\n\n"
        f"## 📣 Urgent Marketing Team Actions\n\n"
        f"## 🎧 Urgent Support Team Actions\n\n"
        f"## 🏆 Top 3 Actions Before Next Week\n"
        f"| Priority | Action | Owner | Expected Outcome |\n"
        f"|----------|--------|-------|------------------|\n\n"
        f"Use real numbers only."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=3000
        )
        report = response.choices[0].message.content.strip()
        os.makedirs("reports", exist_ok=True)
        filename = f"reports/weekly_report_{datetime.now().strftime('%Y_W%U')}.md"
        with open(filename, "w") as f:
            f.write(report)
        print(f"✅ Weekly report saved: {filename}")
        return report
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    generate_global_report()
    generate_weekly_report()
