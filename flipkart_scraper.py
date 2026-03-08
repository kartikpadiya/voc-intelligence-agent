import requests
from bs4 import BeautifulSoup
import json
import time
import random
import csv
from datetime import datetime
import os

HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
]

PRODUCTS = {
    "noise_buds_vs402": {
        "name": "Noise Buds VS402",
        "url": "https://www.flipkart.com/noise-buds-vs402-bluetooth-headset/product-reviews/itm123456?pid=ACCGZ5HFHZGZQMNS&page={page}"
    },
    "noise_air_buds_mini": {
        "name": "Noise Air Buds Mini", 
        "url": "https://www.flipkart.com/noise-air-buds-mini/product-reviews/itm?pid=ACCGZ5HF&page={page}"
    }
}

def get_headers():
    return random.choice(HEADERS_LIST)

def get_flipkart_reviews(product_id, product_name, base_url, max_pages=10):
    all_reviews = []
    
    print(f"\n{'='*50}")
    print(f"Scraping: {product_name}")
    print(f"{'='*50}")
    
    for page in range(1, max_pages + 1):
        url = base_url.format(page=page)
        
        try:
            print(f"  Page {page}...", end=" ")
            
            response = requests.get(
                url,
                headers=get_headers(),
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ Status: {response.status_code}")
                break
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Flipkart review containers
            review_containers = soup.find_all('div', {'class': lambda x: x and 'col' in x and 'EPCmJX' in x})
            
            if not review_containers:
                # Try alternate selectors
                review_containers = soup.find_all('div', {'class': '_1AtVbE'})
            
            if not review_containers:
                review_containers = soup.find_all('div', attrs={'class': lambda x: x and 'review' in x.lower() if x else False})
            
            if not review_containers:
                print(f"⚠️ No reviews found on page {page}")
                # Save HTML for debugging
                with open(f'data/flipkart_debug_p{page}.html', 'w') as f:
                    f.write(response.text[:5000])
                break
            
            page_reviews = []
            for container in review_containers:
                try:
                    # Rating
                    rating_el = container.find('div', {'class': lambda x: x and ('_3LWZlK' in x or 'XQDdHH' in x)})
                    rating = float(rating_el.text.strip()) if rating_el else 0
                    
                    # Title
                    title_el = container.find('p', {'class': lambda x: x and '_2-N8zT' in x})
                    if not title_el:
                        title_el = container.find('p', {'class': 'z9E0IG'})
                    title = title_el.text.strip() if title_el else "No Title"
                    
                    # Review text
                    text_el = container.find('div', {'class': lambda x: x and 't-ZTKy' in x})
                    if not text_el:
                        text_el = container.find('div', {'class': 'ZmyHeo'})
                    text = text_el.text.strip() if text_el else ""
                    
                    # Reviewer name
                    name_el = container.find('p', {'class': lambda x: x and '_2sc7ZR' in x})
                    reviewer = name_el.text.strip() if name_el else "Anonymous"
                    
                    # Date
                    date_el = container.find('p', {'class': '_2sc7ZR'})
                    review_date = date_el.text.strip() if date_el else datetime.now().strftime("%B %d, %Y")
                    
                    if text and len(text) > 10:
                        review = {
                            "product_id": product_id,
                            "product_name": product_name,
                            "rating": rating,
                            "title": title,
                            "text": text,
                            "reviewer": reviewer,
                            "date": review_date,
                            "scraped_at": datetime.now().isoformat(),
                            "source": "flipkart"
                        }
                        page_reviews.append(review)
                        
                except Exception as e:
                    continue
            
            all_reviews.extend(page_reviews)
            print(f"✅ {len(page_reviews)} reviews")
            
            if len(page_reviews) == 0:
                break
                
            # Random delay to avoid detection
            delay = random.uniform(2, 5)
            time.sleep(delay)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error: {e}")
            break
    
    return all_reviews


def save_to_csv(reviews, filename):
    if not reviews:
        print("No reviews to save!")
        return
    
    os.makedirs('data', exist_ok=True)
    filepath = f'data/{filename}'
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['product_id', 'product_name', 'rating', 'title', 'text', 
                     'reviewer', 'date', 'scraped_at', 'source']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reviews)
    
    print(f"\n✅ Saved {len(reviews)} reviews to {filepath}")
    return filepath


def scrape_product_by_url(flipkart_url, product_name, product_id, max_pages=10):
    """Scrape any Flipkart product URL"""
    
    # Convert product URL to review URL
    if '/product-reviews/' not in flipkart_url:
        # Extract product details from URL
        parts = flipkart_url.split('/')
        review_url = flipkart_url.replace('/p/', '/product-reviews/') + '&page={page}'
    else:
        review_url = flipkart_url + '&page={page}' if '{page}' not in flipkart_url else flipkart_url
    
    reviews = get_flipkart_reviews(product_id, product_name, review_url, max_pages)
    return reviews


if __name__ == "__main__":
    print("="*50)
    print("FLIPKART REVIEW SCRAPER")
    print("="*50)
    
    # Test with a URL
    print("\nEnter Flipkart product URL (or press Enter to test with sample):")
    url = input().strip()
    
    if not url:
        # Test URL - Noise Buds
        url = "https://www.flipkart.com/noise-buds-vs402-true-wireless-earbuds/product-reviews/itmf3b7fghzxmqhg?pid=ACCGZ5HFHZGZQMNS"
        print(f"Using test URL: {url}")
    
    print("\nEnter product name (e.g. 'Noise Buds VS402'):")
    name = input().strip() or "Noise Product"
    
    print("\nHow many pages? (1 page = ~10 reviews):")
    try:
        pages = int(input().strip())
    except:
        pages = 5
    
    product_id = name.lower().replace(' ', '_')
    reviews = scrape_product_by_url(url, name, product_id, pages)
    
    if reviews:
        filename = f"flipkart_{product_id}_{datetime.now().strftime('%Y%m%d')}.csv"
        save_to_csv(reviews, filename)
        print(f"\n✅ DONE! {len(reviews)} reviews scraped!")
        print(f"File: data/{filename}")
        print(f"\nNow upload this CSV to VocBot web interface!")
    else:
        print("\n⚠️ No reviews scraped!")
        print("Flipkart may have blocked the request.")
        print("Check: data/flipkart_debug_p1.html for the raw response")
