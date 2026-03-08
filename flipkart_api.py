import requests
import json
import csv
import time
import random
from datetime import datetime

def scrape_flipkart_api(product_pid, product_name, product_id, max_pages=10):
    """Use Flipkart's internal API to get reviews"""
    
    all_reviews = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'X-user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 FKUA/fkua-web-app/0.0.1/desktop/website',
        'Referer': f'https://www.flipkart.com/product-reviews/{product_pid}'
    }
    
    print(f"\nScraping: {product_name}")
    print(f"PID: {product_pid}")
    
    for page in range(1, max_pages + 1):
        url = f"https://1.rome.api.flipkart.com/api/4/review/consolidated?pid={product_pid}&pageContext=%7B%22pageNumber%22%3A{page}%7D"
        
        try:
            print(f"  Page {page}...", end=" ")
            response = requests.get(url, headers=headers, timeout=20)
            
            if response.status_code != 200:
                print(f"❌ Status: {response.status_code}")
                break
            
            data = response.json()
            
            # Save raw response for debugging
            with open(f'data/flipkart_api_p{page}.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            # Extract reviews from response
            reviews_found = []
            
            # Navigate the response structure
            try:
                page_data = data.get('RESPONSE', {})
                slots = page_data.get('slots', [])
                
                for slot in slots:
                    widget = slot.get('widget', {})
                    data_obj = widget.get('data', {})
                    reviews_list = data_obj.get('reviews', [])
                    
                    for r in reviews_list:
                        try:
                            review = {
                                "product_id": product_id,
                                "product_name": product_name,
                                "rating": r.get('rating', 0),
                                "title": r.get('title', 'No Title'),
                                "text": r.get('reviewText', ''),
                                "reviewer": r.get('reviewer', {}).get('name', 'Anonymous'),
                                "date": r.get('reviewAge', datetime.now().strftime("%B %d, %Y")),
                                "scraped_at": datetime.now().isoformat(),
                                "source": "flipkart"
                            }
                            if review['text']:
                                reviews_found.append(review)
                        except:
                            continue
            except:
                pass
            
            print(f"✅ {len(reviews_found)} reviews")
            all_reviews.extend(reviews_found)
            
            if not reviews_found:
                print("  Checking raw response structure...")
                print(f"  Keys: {list(data.keys())[:5]}")
                break
            
            time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            print(f"❌ Error: {e}")
            break
    
    return all_reviews


if __name__ == "__main__":
    print("="*50)
    print("FLIPKART API SCRAPER")
    print("="*50)
    
    print("\nFlipkart product URL paste karo:")
    url = input().strip()
    
    # Extract PID from URL
    pid = ""
    if "pid=" in url:
        pid = url.split("pid=")[1].split("&")[0]
    elif "/p/" in url:
        parts = url.split("/")
        for i, p in enumerate(parts):
            if p == "p" and i+1 < len(parts):
                pid = parts[i+1].split("?")[0]
    
    if not pid:
        print("PID manually daalo (URL mein pid= ke baad wala):")
        pid = input().strip()
    
    print(f"PID: {pid}")
    
    print("Product name:")
    name = input().strip() or "Noise Product"
    
    print("Max pages (default 5):")
    try:
        pages = int(input().strip())
    except:
        pages = 5
    
    product_id = name.lower().replace(' ', '_')
    reviews = scrape_flipkart_api(pid, name, product_id, pages)
    
    if reviews:
        filename = f"data/flipkart_{product_id}_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=reviews[0].keys())
            writer.writeheader()
            writer.writerows(reviews)
        print(f"\n✅ {len(reviews)} reviews saved!")
        print(f"File: {filename}")
        print(f"Upload this to VocBot!")
    else:
        print("\n⚠️ No reviews - check data/flipkart_api_p1.json for structure")
