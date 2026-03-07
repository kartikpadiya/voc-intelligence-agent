import csv
import json
import os
import sqlite3
from datetime import datetime
from database import init_database, DB_PATH

RAW_CSV = "data/amazon-review-data.csv"

PRODUCT_MAP = {
    "EarFun": {
        "product_id": "master_buds_1",
        "product_name": "Master Buds 1 (EarFun)"
    },
    "Apple": {
        "product_id": "master_buds_max",
        "product_name": "Master Buds Max (Apple AirPods)"
    }
}

def clean_text(text):
    if not text:
        return ""
    text = text.strip()
    text = text.replace('\r', ' ').replace('\n', ' ')
    text = ' '.join(text.split())
    return text[:2000]


def clean_rating(rating_str):
    try:
        rating = float(str(rating_str).strip())
        if 1.0 <= rating <= 5.0:
            return rating
        return None
    except:
        return None


def clean_date(date_str):
    if not date_str:
        return ""
    date_str = date_str.strip()
    formats = [
        "%d-%b-%y",
        "%d-%b-%Y",
        "%B %d, %Y",
        "%Y-%m-%d"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("Reviewed on %B %d, %Y")
        except:
            continue
    return date_str


def parse_and_load():
    print("="*50)
    print("VOC Agent - Data Parser Starting")
    print("="*50)

    if not os.path.exists(RAW_CSV):
        print(f"ERROR: {RAW_CSV} not found!")
        return

    init_database()

    stats = {
        "total_read": 0,
        "master_buds_1": 0,
        "master_buds_max": 0,
        "skipped": 0,
        "duplicates": 0
    }

    cleaned_reviews = []

    print(f"\nReading {RAW_CSV}...")

    with open(RAW_CSV, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            stats["total_read"] += 1

            # Get brand
            brand = clean_text(row.get("productBrand", ""))

            # Only process EarFun and Apple
            if brand not in PRODUCT_MAP:
                stats["skipped"] += 1
                continue

            # Clean all fields
            rating = clean_rating(row.get("overall", ""))
            if rating is None:
                stats["skipped"] += 1
                continue

            title = clean_text(row.get("reviewTitle", ""))
            text = clean_text(row.get("reviewText", ""))
            date = clean_date(row.get("reviewTime", ""))
            reviewer = clean_text(row.get("reviewerName", "Anonymous"))

            # Skip if no review text
            if not text or len(text) < 10:
                stats["skipped"] += 1
                continue

            product_info = PRODUCT_MAP[brand]

            review = {
                "product_id": product_info["product_id"],
                "product_name": product_info["product_name"],
                "rating": rating,
                "title": title if title else f"{rating} star review",
                "text": text,
                "date": date,
                "reviewer": reviewer,
                "scraped_at": datetime.now().isoformat()
            }

            cleaned_reviews.append(review)

    print(f"Total rows read: {stats['total_read']}")
    print(f"Skipped (wrong brand/bad data): {stats['skipped']}")
    print(f"Clean reviews ready: {len(cleaned_reviews)}")

    # Save cleaned reviews to JSON files per product
    for product_id in ["master_buds_1", "master_buds_max"]:
        product_reviews = [
            r for r in cleaned_reviews 
            if r["product_id"] == product_id
        ]

        # Limit to 1000 per product
        product_reviews = product_reviews[:1000]

        filepath = f"data/{product_id}_raw.json"
        with open(filepath, "w") as f:
            json.dump(product_reviews, f, indent=2)

        count = len(product_reviews)
        stats[product_id] = count
        print(f"Saved {count} reviews for {product_id} to {filepath}")

    # Now load into database
    print("\nLoading into database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    inserted = 0
    duplicates = 0

    for review in cleaned_reviews[:2000]:
        try:
            review_date_str = review.get("date", "").strip()
            is_new = False
            for fmt in ["%d-%b-%y", "%d/%m/%Y", "%d-%b-%Y", "%Y-%m-%d"]:
                try:
                    from datetime import datetime as dt
                    parsed_date = dt.strptime(review_date_str, fmt)
                    if parsed_date.year >= 2024:
                        is_new = True
                    break
                except:
                    continue
            week_added = datetime.now().strftime("%Y-W%U") if is_new else "2025-W01"

            cursor.execute('''
                INSERT OR IGNORE INTO reviews
                (product_id, product_name, rating, title, text, 
                date, reviewer, scraped_at, week_added)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                review["product_id"],
                review["product_name"],
                review["rating"],
                review["title"],
                review["text"],
                review["date"],
                review["reviewer"],
                review["scraped_at"],
                week_added
            ))

            if cursor.rowcount > 0:
                inserted += 1
            else:
                duplicates += 1

        except Exception as e:
            print(f"DB Error: {e}")
            continue

    conn.commit()
    conn.close()

    print("\n" + "="*50)
    print("PARSING COMPLETE!")
    print(f"Total inserted into DB: {inserted}")
    print(f"Duplicates skipped: {duplicates}")
    print(f"Master Buds 1 (EarFun): {stats['master_buds_1']} reviews")
    print(f"Master Buds Max (Apple): {stats['master_buds_max']} reviews")
    print("="*50)


if __name__ == "__main__":
    parse_and_load()
