import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "data/voc_reviews.db"

def init_database():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            rating REAL,
            title TEXT,
            text TEXT,
            date TEXT,
            reviewer TEXT,
            sentiment TEXT,
            themes TEXT,
            scraped_at TEXT,
            week_added TEXT,
            UNIQUE(reviewer, date, rating, product_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS run_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT,
            product_id TEXT,
            new_reviews_count INTEGER,
            total_reviews_count INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


def insert_reviews(reviews):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    new_count = 0
    week_added = datetime.now().strftime("%Y-W%U")
    
    for review in reviews:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO reviews 
                (product_id, product_name, rating, title, text, date, reviewer, scraped_at, week_added)
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
                new_count += 1
                
        except Exception as e:
            print(f"Error inserting review: {e}")
            continue
    
    conn.commit()
    conn.close()
    print(f"Inserted {new_count} new reviews into database")
    return new_count


def get_all_reviews(product_id=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if product_id:
        cursor.execute(
            "SELECT * FROM reviews WHERE product_id = ?", 
            (product_id,)
        )
    else:
        cursor.execute("SELECT * FROM reviews")
    
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]


def get_weekly_reviews():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    current_week = datetime.now().strftime("%Y-W%U")
    cursor.execute(
        "SELECT * FROM reviews WHERE week_added = ?", 
        (current_week,)
    )
    
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]


def update_sentiment_and_themes(review_id, sentiment, themes):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE reviews 
        SET sentiment = ?, themes = ?
        WHERE id = ?
    ''', (sentiment, json.dumps(themes), review_id))
    
    conn.commit()
    conn.close()


def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM reviews")
    total = cursor.fetchone()[0]
    
    cursor.execute(
        "SELECT product_id, COUNT(*) FROM reviews GROUP BY product_id"
    )
    by_product = cursor.fetchall()
    
    cursor.execute(
        "SELECT sentiment, COUNT(*) FROM reviews GROUP BY sentiment"
    )
    by_sentiment = cursor.fetchall()
    
    conn.close()
    
    return {
        "total": total,
        "by_product": dict(by_product),
        "by_sentiment": dict(by_sentiment)
    }


def log_run(product_id, new_count, total_count):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO run_logs (run_date, product_id, new_reviews_count, total_reviews_count)
        VALUES (?, ?, ?, ?)
    ''', (datetime.now().isoformat(), product_id, new_count, total_count))
    
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_database()
    print("Database ready!")
    print(get_stats())
