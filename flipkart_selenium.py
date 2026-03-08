from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import random
import csv
from datetime import datetime

def get_driver():
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def scrape_flipkart(url, product_name, product_id, max_pages=5):
    driver = get_driver()
    all_reviews = []
    
    print(f"Opening browser for: {product_name}")
    
    try:
        for page in range(1, max_pages + 1):
            page_url = f"{url}&page={page}" if '?' in url else f"{url}?page={page}"
            print(f"  Page {page}...", end=" ")
            
            driver.get(page_url)
            time.sleep(random.uniform(3, 5))
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Save debug
            with open(f'data/flipkart_debug_p{page}.html', 'w') as f:
                f.write(driver.page_source[:10000])
            
            # Try multiple selectors
            reviews = []
            
            # Selector 1
            containers = soup.find_all('div', {'class': 'col EPCmJX Ma-has'})
            # Selector 2
            if not containers:
                containers = soup.find_all('div', class_=lambda x: x and 'EPCmJX' in x)
            # Selector 3
            if not containers:
                containers = soup.find_all('div', {'class': '_1AtVbE col-12-12'})

            for c in containers:
                try:
                    rating = c.find('div', class_=lambda x: x and 'XQDdHH' in x)
                    title = c.find('p', class_=lambda x: x and 'z9E0IG' in x)
                    text = c.find('div', class_=lambda x: x and 'ZmyHeo' in x)
                    
                    if text and len(text.text.strip()) > 10:
                        reviews.append({
                            "product_id": product_id,
                            "product_name": product_name,
                            "rating": float(rating.text.strip()) if rating else 0,
                            "title": title.text.strip() if title else "No Title",
                            "text": text.text.strip(),
                            "reviewer": "Flipkart User",
                            "date": datetime.now().strftime("%B %d, %Y"),
                            "scraped_at": datetime.now().isoformat(),
                            "source": "flipkart"
                        })
                except:
                    continue
            
            print(f"✅ {len(reviews)} reviews")
            all_reviews.extend(reviews)
            
            if not reviews:
                print("No more reviews found!")
                break
                
    finally:
        driver.quit()
    
    return all_reviews

if __name__ == "__main__":
    print("Enter Flipkart product reviews URL:")
    url = input().strip()
    
    print("Product name:")
    name = input().strip() or "Noise Product"
    
    print("Max pages (default 5):")
    try:
        pages = int(input().strip())
    except:
        pages = 5
    
    product_id = name.lower().replace(' ', '_')
    reviews = scrape_flipkart(url, name, product_id, pages)
    
    if reviews:
        filename = f"data/flipkart_{product_id}_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=reviews[0].keys())
            writer.writeheader()
            writer.writerows(reviews)
        print(f"\n✅ {len(reviews)} reviews saved to {filename}")
        print("Now upload this CSV to VocBot!")
    else:
        print("\n⚠️ No reviews found - check data/flipkart_debug_p1.html")
