


import asyncio
import random
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

PRODUCTS = {
    "master_buds_1": {
        "name": "Master Buds 1",
        "url": "https://www.amazon.in/Sony-WF-1000XM4-Cancellation-Headphones-WF1000XM4/product-reviews/B094C57GLC/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews"
    },
    "master_buds_max": {
        "name": "Master Buds Max",
        "url": "https://www.amazon.in/Apple-AirPods-Pro-2nd-Generation/product-reviews/B0BDHWDR12/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews"
    }
}

async def scrape_reviews(product_key, max_pages=10):
    product = PRODUCTS[product_key]
    reviews = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled'
            ]
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        page = await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        current_url = product["url"]
        page_num = 1

        while page_num <= max_pages and current_url:
            try:
                print(f"Scraping {product['name']} - Page {page_num}...")

                await page.goto(current_url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(random.uniform(2, 4))

                review_elements = await page.query_selector_all('[data-hook="review"]')

                if not review_elements:
                    print(f"No reviews found on page {page_num}, stopping.")
                    break

                for element in review_elements:
                    try:
                        rating_el = await element.query_selector('[data-hook="review-star-rating"] span')
                        rating_text = await rating_el.inner_text() if rating_el else "0"
                        rating = float(rating_text.split(" ")[0]) if rating_text else 0.0

                        title_el = await element.query_selector('[data-hook="review-title"] span:not([class])')
                        if not title_el:
                            title_el = await element.query_selector('[data-hook="review-title"]')
                        title = await title_el.inner_text() if title_el else "No Title"

                        text_el = await element.query_selector('[data-hook="review-body"] span')
                        text = await text_el.inner_text() if text_el else "No Text"

                        date_el = await element.query_selector('[data-hook="review-date"]')
                        date_text = await date_el.inner_text() if date_el else ""

                        name_el = await element.query_selector('.a-profile-name')
                        reviewer = await name_el.inner_text() if name_el else "Anonymous"

                        review = {
                            "product_id": product_key,
                            "product_name": product["name"],
                            "rating": rating,
                            "title": title.strip(),
                            "text": text.strip(),
                            "date": date_text.strip(),
                            "reviewer": reviewer.strip(),
                            "scraped_at": datetime.now().isoformat()
                        }

                        reviews.append(review)

                    except Exception as e:
                        print(f"Error parsing review: {e}")
                        continue

                print(f"  Got {len(review_elements)} reviews from page {page_num}")

                next_button = await page.query_selector('li.a-last a')
                if next_button:
                    next_href = await next_button.get_attribute('href')
                    if next_href:
                        current_url = f"https://www.amazon.in{next_href}"
                        page_num += 1
                    else:
                        break
                else:
                    break

            except Exception as e:
                print(f"Error on page {page_num}: {e}")
                break

        await browser.close()

    print(f"Total reviews scraped for {product['name']}: {len(reviews)}")
    return reviews


def save_raw_reviews(reviews, product_key):
    os.makedirs("data", exist_ok=True)
    filepath = f"data/{product_key}_raw.json"

    existing = []
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            existing = json.load(f)

    all_reviews = existing + reviews
    seen = set()
    unique = []
    for r in all_reviews:
        key = f"{r['reviewer']}_{r['date']}_{r['rating']}"
        if key not in seen:
            seen.add(key)
            unique.append(r)

    with open(filepath, "w") as f:
        json.dump(unique, f, indent=2)

    new_count = len(unique) - len(existing)
    print(f"Saved {len(unique)} total reviews ({new_count} new) to {filepath}")
    return new_count


async def run_scraper():
    print("="*50)
    print("VOC Agent - Scraper Starting")
    print("="*50)

    for product_key in PRODUCTS:
        reviews = await scrape_reviews(product_key, max_pages=10)
        save_raw_reviews(reviews, product_key)

    print("\nScraping Complete!")


if __name__ == "__main__":
    asyncio.run(run_scraper())
