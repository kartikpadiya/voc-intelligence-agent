import requests
from bs4 import BeautifulSoup
import csv
import time
import random
from datetime import datetime

SCRAPER_API_KEY = "YOUR_API_KEY_HERE"

def scrape_with_api(flipkart_url, product_name, product_id, max_pages=5):
    all_reviews = []
    
    print(f"Scraping: {product_name}")
    
    for page in range(1, max_pages + 1):
        page_url = f"{flipkart_url}&page={page}"
        api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={page_url}&country_code=in&render=true&premium=true"
        
        print(f"  Page {page}...", end=" ", flush=True)
        
        try:
            response = requests.get(api_url, timeout=60)
            
            if response.status_code != 200:
                print(f"❌ Status: {response.status_code}")
                break
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Save debug
            with open(f'data/scraper_debug_p{page}.html', 'w') as f:
                f.write(response.text[:30000])
            
            reviews_found = []
            
            # Try all possible selectors
            selectors = [
                ('div', {'class': lambda x: x and 'EPCmJX' in x}),
                ('div', {'class': lambda x: x and 'ZmyHeo' in x}),
                ('div', {'class': '_1AtVbE col-12-12'}),
            ]
            
            containers = []
            for tag, attrs in selectors:
                containers = soup.find_all(tag, attrs)
                if containers:
                    break
            
            for c in containers:
                try:
                    text_el = c.find('div', class_=lambda x: x and 'ZmyHeo' in x)
                    if not text_el:
                        text_el = c.find('div', class_=lambda x: x and 't-ZTKy' in x)
                    
                    rating_el = c.find('div', class_=lambda x: x and 'XQDdHH' in x)
                    title_el = c.find('p', class_=lambda x: x and 'z9E0IG' in x)
                    
                    text = text_el.text.strip() if text_el else ""
                    if text and len(text) > 10:
                        reviews_found.append({
                            "product_id": product_id,
                            "product_name": product_name,
                            "rating": float(rating_el.text.strip()) if rating_el else 0,
                            "title": title_el.text.strip() if title_el else "No Title",
                            "text": text,
                            "reviewer": "Flipkart User",
                            "date": datetime.now().strftime("%B %d, %Y"),
                            "scraped_at": datetime.now().isoformat(),
                            "source": "flipkart"
                        })
                except:
                    continue
            
            print(f"✅ {len(reviews_found)} reviews")
            all_reviews.extend(reviews_found)
            
            if not reviews_found:
                print("  No reviews - check scraper_debug_p1.html")
                break
            
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"❌ {e}")
            break
    
    return all_reviews


if __name__ == "__main__":
    print("="*50)
    print("FLIPKART SCRAPERAPI SCRAPER")
    print("="*50)
    
    print("\nScraperAPI Key daalo:")
    key = input().strip()
    if key:
        SCRAPER_API_KEY = key
    
    print("\nFlipkart reviews URL:")
    url = input().strip()
    
    print("Product name:")
    name = input().strip() or "Noise Product"
    
    print("Max pages (default 5):")
    try:
        pages = int(input().strip())
    except:
        pages = 5
    
    product_id = name.lower().replace(' ', '_')
    reviews = scrape_with_api(url, name, product_id, pages)
    
    if reviews:
        filename = f"data/flipkart_{product_id}_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=reviews[0].keys())
            writer.writeheader()
            writer.writerows(reviews)
        print(f"\n✅ {len(reviews)} reviews saved!")
        print(f"File: {filename}")
    else:
        print("\n⚠️ No reviews found!")
