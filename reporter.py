import os
import json
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from database import get_all_reviews, get_weekly_reviews
from analyzer import get_theme_summary

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def get_actual_counts(reviews):
    total = len(reviews)
    if total == 0:
        return {}
    keywords = {
        "noise cancellation": 0, "bluetooth": 0, "battery": 0,
        "app crash": 0, "uncomfortable": 0, "fall out": 0,
        "return": 0, "sound quality": 0, "fit": 0, "anc": 0,
        "disconnect": 0, "lag": 0, "pairing": 0, "bass": 0,
        "mic": 0, "worth": 0, "cheap": 0, "expensive": 0,
        "recommend": 0, "worst": 0, "best": 0, "comfortable": 0,
        "charging": 0, "case": 0, "volume": 0
    }
    for r in reviews:
        text = (r.get("text", "") + " " + r.get("title", "")).lower()
        for keyword in keywords:
            if keyword in text:
                keywords[keyword] += 1
    result = {"total_reviews": total, "keyword_analysis": {}}
    for keyword, count in keywords.items():
        if count > 0:
            percentage = round((count / total) * 100, 1)
            severity = (
                "CRITICAL" if percentage > 20 else
                "HIGH" if percentage > 10 else
                "MEDIUM" if percentage > 5 else "LOW"
            )
            result["keyword_analysis"][keyword] = {
                "mentions": count,
                "out_of": total,
                "percentage": f"{percentage}%",
                "severity": severity
            }
    return result


def get_theme_detailed(reviews):
    total = len(reviews)
    if total == 0:
        return {}
    theme_data = {}
    for r in reviews:
        themes = json.loads(r["themes"]) if r.get("themes") else []
        sentiment = r.get("sentiment", "Neutral")
        rating = r.get("rating", 0)
        for theme in themes:
            if theme not in theme_data:
                theme_data[theme] = {
                    "total_mentions": 0, "Positive": 0,
                    "Negative": 0, "Neutral": 0,
                    "ratings": [], "percentage_of_reviews": 0, "health": ""
                }
            theme_data[theme]["total_mentions"] += 1
            theme_data[theme][sentiment] += 1
            theme_data[theme]["ratings"].append(rating)
    for theme in theme_data:
        total_mentions = theme_data[theme]["total_mentions"]
        percentage = round((total_mentions / total) * 100, 1)
        theme_data[theme]["percentage_of_reviews"] = f"{percentage}%"
        avg_rating = round(
            sum(theme_data[theme]["ratings"]) /
            len(theme_data[theme]["ratings"]), 1
        )
        theme_data[theme]["avg_rating"] = avg_rating
        del theme_data[theme]["ratings"]
        pos = theme_data[theme]["Positive"]
        neg = theme_data[theme]["Negative"]
        if neg > pos:
            theme_data[theme]["health"] = "PROBLEM AREA"
        elif pos > neg * 2:
            theme_data[theme]["health"] = "STRENGTH"
        else:
            theme_data[theme]["health"] = "MIXED"
    return theme_data


def get_rating_distribution(reviews):
    total = len(reviews)
    dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in reviews:
        rating = int(r.get("rating", 3))
        if rating in dist:
            dist[rating] += 1
    result = {}
    for rating, count in dist.items():
        percentage = round((count / total) * 100, 1) if total > 0 else 0
        result[f"{rating}_star"] = {
            "count": count,
            "percentage": f"{percentage}%"
        }
    avg = round(
        sum(r.get("rating", 0) for r in reviews) / total, 2
    ) if total > 0 else 0
    result["average_rating"] = avg
    return result


def get_sentiment_distribution(reviews):
    total = len(reviews)
    counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
    for r in reviews:
        if r.get("sentiment"):
            s = r.get("sentiment", "Neutral")
            counts[s] = counts.get(s, 0) + 1
    result = {}
    for sentiment, count in counts.items():
        percentage = round((count / total) * 100, 1) if total > 0 else 0
        result[sentiment] = {
            "count": count,
            "percentage": f"{percentage}%"
        }
    return result


def get_review_samples(reviews, sentiment, limit=5):
    filtered = [
        r for r in reviews if r.get("sentiment") == sentiment
    ][:limit]
    return [
        f"[{r['rating']}star] {r['title']}: {r['text'][:250]}"
        for r in filtered
    ]


def build_deep_context(reviews, limit=80):
    analyzed = [r for r in reviews if r.get("sentiment")][:limit]
    lines = []
    for r in analyzed:
        themes = json.loads(r["themes"]) if r.get("themes") else []
        lines.append(
            f"[{r['sentiment']}][Rating:{r['rating']}][{', '.join(themes)}] "
            f"Title: {r['title']} | Review: {r['text'][:250]}"
        )
    return "\n".join(lines)


def generate_single_product_report(product_id, product_name, reviews, today):
    print(f"Analyzing {product_name}...")

    context = build_deep_context(reviews)
    counts = get_actual_counts(reviews)
    themes = get_theme_detailed(reviews)
    rating_dist = get_rating_distribution(reviews)
    sentiment_dist = get_sentiment_distribution(reviews)
    neg_samples = get_review_samples(reviews, "Negative", 5)
    pos_samples = get_review_samples(reviews, "Positive", 4)

    prompt = (
        f"You are a senior Voice of Customer Analyst.\n"
        f"Analyze reviews for {product_name} and generate a detailed report.\n"
        f"Use ONLY real numbers from data provided. Never make up frequencies.\n\n"
        f"=== {product_name} Reviews ===\n" + context + "\n\n"
        "=== Rating Distribution ===\n" + json.dumps(rating_dist, indent=2) + "\n\n"
        "=== Sentiment Distribution ===\n" + json.dumps(sentiment_dist, indent=2) + "\n\n"
        "=== Theme Analysis ===\n" + json.dumps(themes, indent=2) + "\n\n"
        "=== Keyword Frequency ===\n" + json.dumps(counts, indent=2) + "\n\n"
        "=== Negative Reviews ===\n" + "\n".join(neg_samples) + "\n\n"
        "=== Positive Reviews ===\n" + "\n".join(pos_samples) + "\n\n"
        f"Generate report for {product_name} with EXACTLY these sections:\n\n"
        f"# {product_name} — Product Intelligence Report\n"
        f"## Generated: {today}\n\n"
        "## Product Health Scorecard\n"
        "Overall Rating, Sentiment Split, Health Score out of 10, Biggest Strength, Biggest Weakness.\n\n"
        "## Theme Analysis\n"
        "For each theme: mention count, percentage, STRENGTH/PROBLEM AREA/MIXED, customer quote.\n\n"
        "## PRODUCT TEAM ACTION ITEMS\n\n"
        "### Recurring Bugs and Crashes\n"
        "Format: Bug - X mentions out of Y reviews (Z%) - Severity\n\n"
        "### Hardware Design Issues\n"
        "Physical problems with frequency and review quotes.\n\n"
        "### Software and App Issues\n"
        "App/firmware issues with frequency.\n\n"
        "### Features To Fix - Priority Order\n"
        "Rank by negative mention percentage. Show actual data.\n\n"
        "### Features Working Well - Do Not Break\n"
        "Highest positive mention counts with evidence.\n\n"
        "## MARKETING TEAM ACTION ITEMS\n\n"
        "### What To Highlight In Ads\n"
        "Top features with actual positive sentiment percentage.\n\n"
        "### What To Stop Claiming\n"
        "Features where negative mentions exceed 10 percent.\n\n"
        "### Target Audience Insights\n"
        "Who is buying this product based on review language.\n\n"
        "## SUPPORT TEAM ACTION ITEMS\n\n"
        "### Top 10 Most Common Complaints\n"
        "Ranked by frequency with actual numbers.\n\n"
        "### Troubleshooting Guides Needed\n"
        "Specific guides based on recurring issues.\n\n"
        "### FAQs To Create\n"
        "Questions customers keep asking.\n\n"
        "### Red Flag Issues\n"
        "Issues where customers mention returning product.\n\n"
        "### Customer Effort Score\n"
        "How hard customers work to fix issues themselves.\n\n"
        "## VERBATIM CUSTOMER VOICE\n"
        "3 best positive quotes, 3 worst negative quotes.\n\n"
        "## TOP 5 RECOMMENDATIONS\n"
        "Format: What, Why with data, Expected Impact.\n\n"
        "CRITICAL: Every number must come from provided data."
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
        print(f"Error for {product_name}: {e}")
        return None


def generate_comparison_report(report1, report2, today):
    print("Generating comparison and combined report...")

    prompt = (
        "You are a senior Voice of Customer Analyst.\n"
        "Based on these two product reports, generate a Head to Head comparison.\n\n"
        "=== MASTER BUDS 1 REPORT ===\n" + report1[:2000] + "\n\n"
        "=== MASTER BUDS MAX REPORT ===\n" + report2[:2000] + "\n\n"
        "Generate EXACTLY these sections:\n\n"
        "# Head To Head Comparison — Master Buds 1 vs Master Buds Max\n"
        f"## Generated: {today}\n\n"
        "## Overall Winner\n"
        "Which product wins overall and why based on data.\n\n"
        "## Feature by Feature Comparison\n"
        "| Feature | Master Buds 1 | Master Buds Max | Winner |\n"
        "|---------|--------------|-----------------|--------|\n"
        "Fill: Sound Quality, ANC, Battery Life, Comfort/Fit, "
        "App Experience, Build Quality, Price/Value\n\n"
        "## What Master Buds 1 Does Better\n"
        "Specific advantages with data evidence.\n\n"
        "## What Master Buds Max Does Better\n"
        "Specific advantages with data evidence.\n\n"
        "## Common Issues Across Both Products\n"
        "Problems affecting both products.\n\n"
        "## Customer Switching Patterns\n"
        "Are customers switching between these products? Why?\n\n"
        "## Combined Top 5 Recommendations\n"
        "Most impactful improvements across both products."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating comparison: {e}")
        return None


def generate_global_report():
    print("="*50)
    print("Generating Deep Global Action Items Report...")
    print("Splitting into 3 focused API calls for quality...")
    print("="*50)

    product1_reviews = get_all_reviews("master_buds_1")
    product2_reviews = get_all_reviews("master_buds_max")

    if not any(
        r.get("sentiment") for r in product1_reviews + product2_reviews
    ):
        print("No analyzed reviews yet! Run analyzer.py first.")
        return None

    today = datetime.now().strftime("%Y-%m-%d")

    # Call 1: Master Buds 1
    report1 = generate_single_product_report(
        "master_buds_1", "Master Buds 1 (EarFun)",
        product1_reviews, today
    )

    # Call 2: Master Buds Max
    report2 = generate_single_product_report(
        "master_buds_max", "Master Buds Max (Apple AirPods)",
        product2_reviews, today
    )

    # Call 3: Comparison
    comparison = generate_comparison_report(report1, report2, today)

    # Combine all 3
    final_report = (
        f"# Global Voice of Customer Intelligence Report\n"
        f"## Generated: {today}\n\n"
        f"---\n\n"
        + (report1 or "") + "\n\n"
        + "---\n\n"
        + (report2 or "") + "\n\n"
        + "---\n\n"
        + (comparison or "")
    )

    os.makedirs("reports", exist_ok=True)
    filename = f"reports/global_report_{datetime.now().strftime('%Y%m%d')}.md"

    with open(filename, "w") as f:
        f.write(final_report)

    print(f"\nGlobal report saved to {filename}")
    return final_report


def generate_weekly_report():
    print("="*50)
    print("Generating Deep Weekly Delta Report...")
    print("="*50)

    weekly_reviews = get_weekly_reviews()
    if not weekly_reviews:
        print("No new reviews this week!")
        return None

    analyzed = [r for r in weekly_reviews if r.get("sentiment")]
    if not analyzed:
        print("Weekly reviews not analyzed yet!")
        return None

    context = build_deep_context(weekly_reviews)
    counts = get_actual_counts(weekly_reviews)
    themes = get_theme_detailed(weekly_reviews)
    rating_dist = get_rating_distribution(weekly_reviews)
    sentiment_dist = get_sentiment_distribution(weekly_reviews)
    neg_samples = get_review_samples(weekly_reviews, "Negative", 5)
    pos_samples = get_review_samples(weekly_reviews, "Positive", 5)

    week = datetime.now().strftime("%Y-W%U")
    total = str(len(weekly_reviews))

    prompt = (
        "You are a senior Voice of Customer Analyst.\n"
        "Based on THIS WEEK new reviews ONLY generate Weekly Delta Report.\n"
        "Use ONLY real numbers. Never guess.\n\n"
        "=== This Week Reviews ===\n" + context + "\n\n"
        "=== Rating Distribution ===\n" + json.dumps(rating_dist, indent=2) + "\n\n"
        "=== Sentiment Distribution ===\n" + json.dumps(sentiment_dist, indent=2) + "\n\n"
        "=== Theme Analysis ===\n" + json.dumps(themes, indent=2) + "\n\n"
        "=== Keyword Frequency ===\n" + json.dumps(counts, indent=2) + "\n\n"
        "=== Worst Reviews ===\n" + "\n".join(neg_samples) + "\n\n"
        "=== Best Reviews ===\n" + "\n".join(pos_samples) + "\n\n"
        "# Weekly Delta Report\n"
        "## Week: " + week + "\n"
        "## Total New Reviews: " + total + "\n\n"
        "## Weekly Summary\n"
        "4-5 sentences with actual numbers.\n\n"
        "## Week At A Glance\n"
        "Total Reviews, Avg Rating, Sentiment Split, Top Theme, Biggest Problem, Biggest Win.\n\n"
        "## Sudden Complaint Spikes\n"
        "High negative frequency with actual counts.\n\n"
        "## Sudden Praise Spikes\n"
        "High positive frequency features.\n\n"
        "## New Bugs Reported\n"
        "Fresh issues this week with review quotes.\n\n"
        "## Recurring Issues Still Present\n"
        "Old problems still mentioned.\n\n"
        "## Urgent Product Team Actions\n\n"
        "## Urgent Marketing Team Actions\n\n"
        "## Urgent Support Team Actions\n\n"
        "## Most Insightful Reviews This Week\n"
        "5 reviews with full quotes.\n\n"
        "## Top 3 Actions Before Next Week\n\n"
        "Use real numbers only."
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
        print(f"Weekly report saved to {filename}")
        return report
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    generate_global_report()
    generate_weekly_report()
