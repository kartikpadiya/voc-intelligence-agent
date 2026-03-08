import os
import json
from groq import Groq
from dotenv import load_dotenv
from database import get_all_reviews, get_weekly_reviews, update_sentiment_and_themes

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

THEMES = [
    "Sound Quality",
    "Battery Life",
    "Comfort/Fit",
    "App Experience",
    "Price/Value",
    "Delivery",
    "Build Quality",
    "ANC"
]

def analyze_review(review):
    prompt = f"""
You are a product review analyst. Analyze this review and return ONLY a JSON object.

Review Title: {review['title']}
Review Text: {review['text']}
Rating: {review['rating']}/5

Return exactly this JSON format with no extra text:
{{
    "sentiment": "Positive" or "Negative" or "Neutral",
    "themes": ["theme1", "theme2"]
}}

Only pick themes from this list:
{json.dumps(THEMES)}

Rules:
- sentiment must be exactly "Positive", "Negative", or "Neutral"
- themes must be a list with 1 to 3 items from the provided list only
- Return ONLY the JSON, nothing else
"""
    try:
        import time
        response = None
        for attempt in range(5):
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=100
                )
                break
            except Exception as retry_err:
                if "429" in str(retry_err):
                    wait = 60 * (attempt + 1)
                    print(f"Rate limit - waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise retry_err
        if response is None:
            return "Neutral", []

        result_text = response.choices[0].message.content.strip()

        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        result = json.loads(result_text)

        sentiment = result.get("sentiment", "Neutral")
        themes = result.get("themes", [])

        if sentiment not in ["Positive", "Negative", "Neutral"]:
            sentiment = "Neutral"
        themes = [t for t in themes if t in THEMES]

        return sentiment, themes

    except Exception as e:
        print(f"Error analyzing review: {e}")
        return "Neutral", []


def analyze_all_reviews():
    print("="*50)
    print("Starting AI Analysis of All Reviews...")
    print("="*50)

    import sqlite3, time
    from database import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT product_id FROM reviews")
    products = [row[0] for row in cursor.fetchall()]
    conn.close()

    for product_id in products:
        reviews = get_all_reviews(product_id)
        unanalyzed = [r for r in reviews if not r.get("sentiment")]
        print(f"\n{product_id}: {len(unanalyzed)} to analyze")
        for i, review in enumerate(unanalyzed):
            print(f"  [{product_id}] {i+1}/{len(unanalyzed)}...", end="\r")
            sentiment, themes = analyze_review(review)
            update_sentiment_and_themes(review["id"], sentiment, themes)
            time.sleep(2)
        print(f"  {product_id} done!")
    print("\nAll products analyzed!")


def analyze_weekly_reviews():
    print("Analyzing this week's new reviews...")

    reviews = get_weekly_reviews()
    unanalyzed = [r for r in reviews if not r.get("sentiment")]

    print(f"Found {len(unanalyzed)} new reviews this week")

    for i, review in enumerate(unanalyzed):
        print(f"Analyzing {i+1}/{len(unanalyzed)}...", end="\r")
        sentiment, themes = analyze_review(review)
        update_sentiment_and_themes(review["id"], sentiment, themes)

    print(f"\nWeekly analysis complete!")


def get_theme_summary(product_id=None):
    reviews = get_all_reviews(product_id)
    analyzed = [r for r in reviews if r.get("sentiment")]

    summary = {}

    for review in analyzed:
        themes = json.loads(review["themes"]) if review.get("themes") else []
        sentiment = review.get("sentiment", "Neutral")

        for theme in themes:
            if theme not in summary:
                summary[theme] = {
                    "Positive": 0,
                    "Negative": 0,
                    "Neutral": 0,
                    "total": 0
                }
            summary[theme][sentiment] += 1
            summary[theme]["total"] += 1

    return summary


def answer_question(question):
    print(f"\nQuestion: {question}")

    product1_reviews = get_all_reviews("master_buds_1")
    product2_reviews = get_all_reviews("master_buds_max")

    def summarize_reviews(reviews, limit=50):
        analyzed = [r for r in reviews if r.get("sentiment")][:limit]
        summaries = []
        for r in analyzed:
            themes = json.loads(r["themes"]) if r.get("themes") else []
            summaries.append(
                f"[{r['sentiment']}][{', '.join(themes)}] "
                f"Rating:{r['rating']} - {r['title']}: {r['text'][:150]}"
            )
        return "\n".join(summaries)

    context1 = summarize_reviews(product1_reviews)
    context2 = summarize_reviews(product2_reviews)

    prompt = f"""
You are a Voice of Customer Analyst. Answer the question based ONLY on the reviews below.
Do not make up information. If data is insufficient, say so.

=== Master Buds 1 Reviews ===
{context1}

=== Master Buds Max Reviews ===
{context2}

Question: {question}

Give a clear, structured answer with specific examples from the reviews.
"""

    try:
        import time
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=800
                )
                break
            except Exception as retry_err:
                if "429" in str(retry_err):
                    import time
                    wait = 60 * (attempt + 1)
                    print(f"Rate limit - waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise retry_err

        answer = response.choices[0].message.content.strip()
        print(f"\nAnswer:\n{answer}")
        return answer

    except Exception as e:
        print(f"Error answering question: {e}")
        return "Unable to answer at this time."


if __name__ == "__main__":
    analyze_all_reviews()

    print("\nTheme Summary:")
    summary = get_theme_summary()
    for theme, counts in summary.items():
        print(f"  {theme}: {counts}")

