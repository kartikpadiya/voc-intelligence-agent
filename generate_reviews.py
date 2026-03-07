import json
import random
import os
from datetime import datetime, timedelta

random.seed(42)

PRODUCTS = {
    "master_buds_1": "Master Buds 1",
    "master_buds_max": "Master Buds Max"
}

POSITIVE_REVIEWS = {
    "master_buds_1": [
        ("Amazing sound quality!", "These earbuds have the best sound I have ever heard. Bass is deep and clear."),
        ("Great ANC!", "Noise cancellation is superb. Blocks out everything on my commute."),
        ("Comfortable fit", "Wore these for 6 hours straight, no discomfort at all."),
        ("Best battery life", "Gets me through the entire workday on single charge. Impressive."),
        ("Worth every penny", "Expensive but totally worth it. Premium feel and sound."),
        ("Excellent build quality", "Feels very premium and sturdy. No cheap plastic feel."),
        ("App is great", "The companion app has tons of customization options. Love it."),
        ("Perfect for gym", "Stay in ears during workouts. Sound is motivating."),
        ("Clear calls", "Call quality is crystal clear. People say I sound great."),
        ("Smooth pairing", "Connects instantly to my phone every single time."),
    ],
    "master_buds_max": [
        ("Apple magic!", "Seamless integration with my iPhone. Just works perfectly."),
        ("Best ANC ever", "Noise cancellation is on another level. Absolute silence."),
        ("Super comfortable", "Lightweight and soft tips make these very comfortable."),
        ("Transparency mode rocks", "Transparency mode is so natural, better than any competitor."),
        ("Premium sound", "Crisp highs and punchy bass. Audiophile level quality."),
        ("Long battery life", "Battery lasts all day easily. Case charges them fast."),
        ("Great for calls", "Microphone picks up voice perfectly even in noisy places."),
        ("Spatial audio is amazing", "Spatial audio makes movies feel like cinema experience."),
        ("Easy switching", "Switches between iPhone iPad and Mac automatically. Genius."),
        ("Worth the price", "Expensive yes but the quality justifies every rupee spent."),
    ]
}

NEGATIVE_REVIEWS = {
    "master_buds_1": [
        ("Too expensive", "Good product but price is way too high for what you get."),
        ("ANC could be better", "Noise cancellation is okay but not great in very loud places."),
        ("App has bugs", "Companion app crashes sometimes. Needs better optimization."),
        ("Average battery", "Battery life is just okay. Expected more for this price."),
        ("Fit issues", "Ear tips dont fit my ears well. Falls out during running."),
        ("Call quality poor", "People complain they cant hear me clearly on calls."),
        ("Bass is too heavy", "Too much bass for my taste. Sounds muddy sometimes."),
        ("No volume control", "Cannot control volume directly on earbuds. Annoying."),
        ("Connectivity drops", "Bluetooth drops randomly. Very frustrating during commute."),
        ("Overpriced", "Not worth the premium price. Many cheaper options sound same."),
    ],
    "master_buds_max": [
        ("Way too expensive", "Price is ridiculous. Only for Apple fanboys honestly."),
        ("Only works with Apple", "Useless if you dont have iPhone. Very limited compatibility."),
        ("ANC not perfect", "ANC lets in low frequency sounds like AC noise. Disappointing."),
        ("Tips fall off", "Ear tips come off inside the ear canal. Disgusting and annoying."),
        ("No customization", "Cannot customize sound profile at all. Very limiting."),
        ("Case scratches easily", "White case gets dirty and scratches within days of use."),
        ("Mediocre call quality", "Microphone is average. Expected better for this price point."),
        ("Battery drains fast", "ANC drains battery very quickly. Barely lasts 4 hours with ANC."),
        ("Uncomfortable for big ears", "Ear tips are too small for my ears. Painful after 2 hours."),
        ("Overrated product", "Just paying for Apple logo. Sound is not worth the premium."),
    ]
}

NEUTRAL_REVIEWS = {
    "master_buds_1": [
        ("Decent earbuds", "Sound is good but nothing extraordinary. Gets the job done."),
        ("Average product", "Neither great nor bad. Just an average pair of earbuds."),
        ("Mixed feelings", "Some features are great but others are disappointing."),
        ("Okay for price", "Fair product at this price point. Could be better though."),
        ("Works as expected", "Does what it promises. No surprises good or bad."),
    ],
    "master_buds_max": [
        ("Just okay", "Expected more from Apple. Sound is good but not great."),
        ("Decent but overpriced", "Good earbuds but not worth the Apple premium honestly."),
        ("Mixed bag", "Some things are great like ANC but battery could be better."),
        ("Average experience", "Nothing special. Many cheaper alternatives are as good."),
        ("Could be better", "Good product but Apple could have done more at this price."),
    ]
}

def random_date():
    start = datetime(2024, 1, 1)
    end = datetime(2026, 2, 28)
    delta = end - start
    random_days = random.randint(0, delta.days)
    return (start + timedelta(days=random_days)).strftime("Reviewed in India on %B %d, %Y")

def random_reviewer():
    names = [
        "Rahul S.", "Priya M.", "Amit K.", "Sneha R.", "Vikram P.",
        "Ananya T.", "Rohan G.", "Deepika N.", "Arjun B.", "Kavya L.",
        "Suresh V.", "Meera J.", "Karan D.", "Pooja H.", "Nikhil C.",
        "Shreya A.", "Aditya W.", "Riya F.", "Mohit Q.", "Divya Z.",
        "Sanjay Y.", "Nisha X.", "Rajesh U.", "Sunita I.", "Varun O.",
        "Ankita E.", "Manish R.", "Swati T.", "Gaurav Y.", "Preeti U."
    ]
    return random.choice(names)

def generate_reviews(product_key, count=600):
    reviews = []

    pos_count = int(count * 0.55)
    neg_count = int(count * 0.30)
    neu_count = count - pos_count - neg_count

    pos_pool = POSITIVE_REVIEWS[product_key]
    neg_pool = NEGATIVE_REVIEWS[product_key]
    neu_pool = NEUTRAL_REVIEWS[product_key]

    for i in range(pos_count):
        title, text = random.choice(pos_pool)
        rating = random.choice([4.0, 5.0, 4.0, 5.0, 5.0])
        extra = random.choice([
            " Really happy with this purchase.",
            " Would recommend to everyone.",
            " Bought it last month and loving it.",
            " Best purchase this year.",
            " My friends are jealous now.",
            ""
        ])
        reviews.append({
            "product_id": product_key,
            "product_name": PRODUCTS[product_key],
            "rating": rating,
            "title": title,
            "text": text + extra,
            "date": random_date(),
            "reviewer": random_reviewer(),
            "scraped_at": datetime.now().isoformat()
        })

    for i in range(neg_count):
        title, text = random.choice(neg_pool)
        rating = random.choice([1.0, 2.0, 1.0, 2.0, 3.0])
        extra = random.choice([
            " Very disappointed.",
            " Returning this product.",
            " Do not recommend.",
            " Expected much better.",
            " Waste of money.",
            ""
        ])
        reviews.append({
            "product_id": product_key,
            "product_name": PRODUCTS[product_key],
            "rating": rating,
            "title": title,
            "text": text + extra,
            "date": random_date(),
            "reviewer": random_reviewer(),
            "scraped_at": datetime.now().isoformat()
        })

    for i in range(neu_count):
        title, text = random.choice(neu_pool)
        rating = 3.0
        reviews.append({
            "product_id": product_key,
            "product_name": PRODUCTS[product_key],
            "rating": rating,
            "title": title,
            "text": text,
            "date": random_date(),
            "reviewer": random_reviewer(),
            "scraped_at": datetime.now().isoformat()
        })

    random.shuffle(reviews)
    return reviews

def main():
    os.makedirs("data", exist_ok=True)

    for product_key in PRODUCTS:
        print(f"Generating reviews for {PRODUCTS[product_key]}...")
        reviews = generate_reviews(product_key, count=600)

        filepath = f"data/{product_key}_raw.json"
        with open(filepath, "w") as f:
            json.dump(reviews, f, indent=2)

        print(f"Saved {len(reviews)} reviews to {filepath}")

    print("\nDone! Reviews generated successfully!")

if __name__ == "__main__":
    main()
