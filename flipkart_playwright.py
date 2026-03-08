import asyncio
import csv
import json
import random
import time
from datetime import datetime
from playwright.async_api import async_playwright

async def scrape_reviews(url, product_name, product_id, max_pages=5):
    all_reviews = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
            ]
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
            locale='en-IN',
        )
        
        # Stealth mode
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
            window.chrome = {runtime: {}};
        """)
        
        page = await context.new_page()
        
        print(f"Opening Flipkart reviews for: {product_name}")
        
        for page_num in range(1, max_pages + 1):
            page_url = f"{url}&page={page_num}" if '?' in url else f"{url}?page={page_num}"
            
            print(f"  Page {page_num}...", end=" ", flush=True)
            
            try:
                await page.goto(page_url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(random.uniform(2, 4))
                
                # Scroll down to load reviews
                await page.evaluate("window.scrollTo(0, 500)")
                await asyncio.sleep(2)
                await page.evaluate("window.scrollTo(0, 1500)")
                await asyncio.sleep(2)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3)

                # Save full HTML for debugging
                html = await page.content()
                with open(f'data/playwright_debug_p{page_num}.html', 'w') as f:
                    f.write(html)  # Save full HTML
                
                # Try to find reviews
                reviews_found = []
                
                # Get all review containers
                containers = await page.query_selector_all('div[class*="EPCmJX"]')
                if not containers:
                    containers = await page.query_selector_all('div[class*="col-12-12"]')
                if not containers:
                    containers = await page.query_selector_all('div[class*="review"]')

                for container in containers:
                    try:
                        # Rating
                        rating_el = await container.query_selector('div[class*="XQDdHH"]')
                        if not rating_el:
                            rating_el = await container.query_selector('div[class*="_3LWZlK"]')
                        rating = float(await rating_el.inner_text()) if rating_el else 0

                        # Title
                        title_el = await container.query_selector('p[class*="z9E0IG"]')
                        if not title_el:
                            title_el = await container.query_selector('p[class*="_2-N8zT"]')
                        title = await title_el.inner_text() if title_el else "No Title"

                        # Text
                        text_el = await container.query_selector('div[class*="ZmyHeo"]')
                        if not text_el:
                            text_el = await container.query_selector('div[class*="t-ZTKy"]')
                        text = await text_el.inner_text() if text_el else ""

                        # Reviewer
                        name_el = await container.query_selector('p[class*="_2sc7ZR"]')
                        reviewer = await name_el.inner_text() if name_el else "Anonymous"

                        if text and len(text.strip()) > 10:
                            reviews_found.append({
                                "product_id": product_id,
                                "product_name": product_name,
                                "rating": rating,
                                "title": title.strip(),
                                "text": text.strip(),
                                "reviewer": reviewer.strip(),
                                "date": datetime.now().strftime("%B %d, %Y"),
                                "scraped_at": datetime.now().isoformat(),
                                "source": "flipkart"
                            })
                    except:
                        continue

                print(f"✅ {len(reviews_found)} reviews")
                all_reviews.extend(reviews_found)

                if not reviews_found:
                    print("  No reviews found - check playwright_debug_p1.html")
                    break

            except Exception as e:
                print(f"❌ Error: {e}")
                break

        await browser.close()
    
    return all_reviews


async def main():
    print("="*50)
    print("FLIPKART PLAYWRIGHT SCRAPER")
    print("="*50)
    
    print("\nFlipkart product reviews URL paste karo:")
    url = input().strip()
    
    print("Product name:")
    name = input().strip() or "Noise Product"
    
    print("Max pages (default 3):")
    try:
        pages = int(input().strip())
    except:
        pages = 3
    
    product_id = name.lower().replace(' ', '_')
    reviews = await scrape_reviews(url, name, product_id, pages)
    
    if reviews:
        filename = f"data/flipkart_{product_id}_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=reviews[0].keys())
            writer.writeheader()
            writer.writerows(reviews)
        print(f"\n✅ {len(reviews)} reviews saved to {filename}")
        print("Upload this CSV to VocBot!")
    else:
        print("\n⚠️ No reviews found!")
        print("Check: data/playwright_debug_p1.html")

if __name__ == "__main__":
    asyncio.run(main())
