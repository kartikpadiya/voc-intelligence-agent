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


def get_products_from_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT product_id, product_name FROM reviews")
    products = cursor.fetchall()
    conn.close()
    return products


def get_theme_tagging(reviews):
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
    for theme in result:
        t = result[theme]["total"]
        if t > 0:
            result[theme]["pct_of_reviews"] = f"{round(t/total*100,1)}%"
            pos = result[theme]["Positive"]
            neg = result[theme]["Negative"]
            if neg > pos:
                result[theme]["health"] = "PROBLEM AREA"
            elif pos > neg * 2:
                result[theme]["health"] = "STRENGTH"
            else:
                result[theme]["health"] = "MIXED"
        else:
            result[theme]["pct_of_reviews"] = "0%"
            result[theme]["health"] = "NO DATA"
    return result


def get_top_issues(reviews):
    keywords = {
        "Bluetooth Disconnects": ["disconnect", "bluetooth drop", "keeps disconnecting"],
        "Poor ANC": ["anc", "noise cancel", "no noise cancel"],
        "App Crashes": ["app crash", "app not working", "app issue"],
        "Uncomfortable Fit": ["uncomfortable", "fall out", "hurts", "pain"],
        "Poor Battery": ["battery drain", "battery life", "dies fast"],
        "Bad Mic Quality": ["mic", "microphone", "call quality"],
        "Lag/Latency": ["lag", "latency", "delay"],
        "Pairing Issues": ["pairing", "won't connect", "connect issue"],
        "Bad Sound Quality": ["sound quality", "bad sound", "tinny", "muffled"],
        "Charging Issues": ["charging", "won't charge", "charge issue"],
        "Poor Build Quality": ["cheap", "broke", "plastic", "flimsy"],
        "Touch Control Issues": ["touch", "controls not working", "accidental"],
    }
    total = len(reviews)
    issues = {}
    for issue, kws in keywords.items():
        count = 0
        samples = []
        for r in reviews:
            text = (r.get("text", "") + " " + r.get("title", "")).lower()
            if any(kw in text for kw in kws):
                count += 1
                if len(samples) < 2:
                    samples.append(f"[{r['rating']}★] {r['text'][:120]}")
        if count > 0:
            pct = round(count / total * 100, 1)
            severity = "CRITICAL" if pct > 20 else "HIGH" if pct > 10 else "MEDIUM" if pct > 5 else "LOW"
            issues[issue] = {
                "count": count,
                "percentage": f"{pct}%",
                "severity": severity,
                "sample_reviews": samples
            }
    return dict(sorted(issues.items(), key=lambda x: x[1]["count"], reverse=True))


def get_top_reviews(reviews, limit=5):
    pos = sorted([r for r in reviews if r.get("sentiment") == "Positive"],
                 key=lambda x: x.get("rating", 0), reverse=True)[:limit]
    neg = sorted([r for r in reviews if r.get("sentiment") == "Negative"],
                 key=lambda x: x.get("rating", 0))[:limit]
    return {
        "top_positive": [f"[{r['rating']}★] {r['title']}: {r['text'][:200]}" for r in pos],
        "top_negative": [f"[{r['rating']}★] {r['title']}: {r['text'][:200]}" for r in neg]
    }


def get_stats(reviews):
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
        "positive": f"{round(pos/total*100,1)}%",
        "negative": f"{round(neg/total*100,1)}%",
        "neutral": f"{round(neu/total*100,1)}%",
    }


def ask_claude(prompt):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=4000
    )
    return response.choices[0].message.content.strip()


def generate_product_report(product_id, product_name, reviews, today):
    print(f"  Claude analyzing {product_name}...")
    analyzed = [r for r in reviews if r.get("sentiment")]
    if not analyzed:
        return f"# {product_name}\nNo analyzed reviews."

    themes = get_theme_tagging(analyzed)
    issues = get_top_issues(analyzed)
    top_reviews = get_top_reviews(analyzed)
    stats = get_stats(analyzed)

    prompt = f"""You are a world-class Voice of Customer analyst working for Noise, India's leading audio brand.

Analyze this real customer review data and generate a detailed, professional report.

PRODUCT: {product_name}
DATE: {today}

=== STATS ===
{json.dumps(stats, indent=2)}

=== THEME-WISE ANALYSIS (Positive/Negative/Neutral per theme) ===
{json.dumps(themes, indent=2)}

=== TOP ISSUES WITH SEVERITY ===
{json.dumps(issues, indent=2)}

=== TOP CUSTOMER REVIEWS ===
{json.dumps(top_reviews, indent=2)}

Generate a comprehensive report with EXACTLY this structure:

# {product_name} — Voice of Customer Report
**Date:** {today}

## 📊 Product Health Snapshot
Summarize overall health in 3-4 sentences using real numbers.

## 🏷️ Theme-Wise Analysis
For ALL 8 themes (Sound Quality, Battery Life, Comfort/Fit, App Experience, Price/Value, Delivery, Build Quality, ANC):
Show a table with:
| Theme | Positive | Negative | Neutral | Health | Insight |
|-------|----------|----------|---------|--------|---------|

Then for each theme give 1 real customer quote.

## ⭐ Top Customer Reviews

### Best Reviews (What Customers Love)
List top 3 positive reviews verbatim with ratings.

### Worst Reviews (What Customers Hate)
List top 3 negative reviews verbatim with ratings.

## 🔴 Top Issues — Severity Ranked
| Issue | Count | % of Reviews | Severity | Action Needed |
|-------|-------|-------------|----------|---------------|
List ALL issues from data, ranked CRITICAL → HIGH → MEDIUM → LOW

## 🛠️ Product Team Actions
5 specific, actionable recommendations with data evidence and priority.

## 📣 Marketing Team Actions
- What to highlight in ads (backed by positive data)
- What to STOP claiming (backed by negative data)
- Target audience insights

## 🎧 Support Team Actions
- Top 5 complaints to resolve
- Troubleshooting guides to create
- FAQs based on real questions

## 🏆 Top 5 Recommendations
| # | Recommendation | Data Evidence | Expected Impact |
|---|---------------|--------------|-----------------|

Be specific, data-driven, and actionable. Use only the data provided."""

    return ask_claude(prompt)


def generate_competitor_report(all_products_data, today):
    print("  Claude generating Competitor Analysis...")
    summaries = {}
    for pid, pname, reviews in all_products_data:
        analyzed = [r for r in reviews if r.get("sentiment")]
        if not analyzed:
            continue
        summaries[pname] = {
            "stats": get_stats(analyzed),
            "themes": {t: {"Positive": d["Positive"], "Negative": d["Negative"], "health": d["health"]}
                      for t, d in get_theme_tagging(analyzed).items()},
            "top_issues": {k: {"count": v["count"], "severity": v["severity"]}
                          for k, v in list(get_top_issues(analyzed).items())[:8]},
            "best_reviews": get_top_reviews(analyzed)["top_positive"][:2],
            "worst_reviews": get_top_reviews(analyzed)["top_negative"][:2],
        }

    names = list(summaries.keys())
    prompt = f"""You are a competitive intelligence analyst at Noise.
Compare these competing audio products using ONLY the provided data.

=== PRODUCT DATA ===
{json.dumps(summaries, indent=2)}

Generate EXACTLY:

# 🏆 Competitor Gap Analysis
**Date:** {today}

## 📊 Head-to-Head Scorecard
| Factor | {" | ".join(names)} | Winner |
|--------|{"--------|" * len(names)}--------|
Fill for: Avg Rating, Positive%, Negative%, Sound Quality health, ANC health, Battery Life health, Comfort/Fit health, App Experience health, Build Quality health, Price/Value health

## 💪 Where Each Product Leads
For each product: top 3 specific advantages with real data.

## ⚠️ Common Weaknesses (Industry Problems)
Issues affecting ALL products — what Noise should solve first.

## 🎯 Issue Comparison Table
| Issue | {" | ".join(names)} |
|-------|{"-------|" * len(names)}
Compare severity of each top issue across products.

## 🚀 Top 3 Gaps Noise Can Win On
Specific opportunities where improvement beats ALL competitors.

## 📣 Positioning Strategy
How to position each Noise product based on actual customer data.

## ⚡ Churn Risk Assessment
Which product has highest customer loss risk and specific reasons.

Use only data provided. Be specific and actionable."""

    return ask_claude(prompt)


def generate_global_report():
    print("=" * 55)
    print("Claude Generating Global VoC Report...")
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
        report = generate_product_report(pid, pname, reviews, today)
        if report:
            product_reports.append(report)

    competitor = generate_competitor_report(all_products_data, today)

    total = sum(len(r[2]) for r in all_products_data)
    final = (
        f"# 🎧 Voice of Customer Intelligence Report\n"
        f"**Generated:** {today} | "
        f"**Products:** {', '.join([p[1] for p in products])} | "
        f"**Total Reviews:** {total}\n\n"
        f"---\n\n"
        + "\n\n---\n\n".join(product_reports)
        + "\n\n---\n\n"
        + (competitor or "")
    )

    os.makedirs("reports", exist_ok=True)
    filename = f"reports/global_report_{datetime.now().strftime('%Y%m%d')}.md"
    with open(filename, "w") as f:
        f.write(final)

    print(f"\n✅ Global report saved: {filename}")
    return final


def generate_weekly_report():
    print("=" * 55)
    print("Claude Generating Weekly Delta Report...")
    print("=" * 55)

    weekly_reviews = get_weekly_reviews()
    if not weekly_reviews:
        print("No new reviews this week!")
        return None

    analyzed = [r for r in weekly_reviews if r.get("sentiment")]
    if not analyzed:
        print("Not analyzed yet!")
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    week = datetime.now().strftime("%Y-W%U")

    themes = get_theme_tagging(analyzed)
    issues = get_top_issues(analyzed)
    top_reviews = get_top_reviews(analyzed)
    stats = get_stats(analyzed)

    all_old = []
    for pid, pname in get_products_from_db():
        reviews = get_all_reviews(pid)
        all_old.extend([r for r in reviews
                       if r.get("week_added") == "2025-W01" and r.get("sentiment")])

    old_stats = get_stats(all_old) if all_old else {}
    old_themes = {t: {"Positive": d["Positive"], "Negative": d["Negative"], "health": d["health"]}
                  for t, d in get_theme_tagging(all_old).items()} if all_old else {}
    old_issues = {k: {"count": v["count"], "severity": v["severity"]}
                  for k, v in list(get_top_issues(all_old).items())[:8]} if all_old else {}

    prompt = f"""You are a senior VoC Analyst at Noise.
Generate a Weekly Delta Report comparing this week vs previous period.
Use ONLY real numbers from the data provided.

=== THIS WEEK ({len(analyzed)} new reviews) ===
Stats: {json.dumps(stats, indent=2)}
Themes: {json.dumps(themes, indent=2)}
Issues: {json.dumps(issues, indent=2)}
Top Reviews: {json.dumps(top_reviews, indent=2)}

=== PREVIOUS PERIOD (baseline) ===
Stats: {json.dumps(old_stats, indent=2)}
Themes: {json.dumps(old_themes, indent=2)}
Issues: {json.dumps(old_issues, indent=2)}

Generate EXACTLY:

# 📅 Weekly Delta Report — {week}
**Date:** {today} | **New Reviews This Week:** {len(analyzed)}

## 📊 Week At A Glance
| Metric | This Week | Previous | Change |
|--------|-----------|----------|--------|
Fill: Avg Rating, Positive%, Negative%, Top Theme, Review Count

## 🏷️ Theme-Wise This Week
| Theme | Positive | Negative | Neutral | Health | vs Last Week |
|-------|----------|----------|---------|--------|-------------|
For ALL 8 themes. Show if better/worse/same vs previous.
Then 1 top customer quote per theme.

## ⭐ Top Reviews This Week
Top 3 positive and top 3 negative verbatim.

## 🔴 Top Issues This Week
| Issue | Count | % | Severity | vs Previous | Trend |
|-------|-------|---|----------|-------------|-------|
Show if issue is NEW, WORSENED, IMPROVED, or SAME vs previous.

## 📈 Complaint Spikes
Issues that INCREASED significantly vs previous period.

## 📉 Improvements
Issues that DECREASED or themes that got better.

## 🛠️ Urgent Product Team Actions
Top 3 urgent actions with data evidence.

## 📣 Urgent Marketing Team Actions
Top 3 urgent actions based on this week's data.

## 🎧 Urgent Support Team Actions
Top 3 urgent actions based on this week's complaints.

## 🏆 Top 3 Actions Before Next Week
| Priority | Action | Owner | Expected Outcome |
|----------|--------|-------|------------------|

Use real numbers only. Be specific."""

    report = ask_claude(prompt)

    os.makedirs("reports", exist_ok=True)
    filename = f"reports/weekly_report_{datetime.now().strftime('%Y_W%U')}.md"
    with open(filename, "w") as f:
        f.write(report)
    print(f"✅ Weekly report saved: {filename}")
    return report


if __name__ == "__main__":
    generate_global_report()
    generate_weekly_report()
