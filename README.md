# VOC Intelligence Agent 🎧

An autonomous AI Agent that analyzes customer reviews for audio products and generates actionable intelligence reports — built for Noise internship assignment.

## Live Demo
Upload any product reviews CSV → AI analyzes → PDF report downloads automatically!

---

## Products Monitored
- **Master Buds 1** (EarFun) — mapped as Noise competitor
- **Master Buds Max** (Apple AirPods) — mapped as Noise competitor

---

## Features
- ✅ CSV upload → automated full pipeline
- ✅ AI-powered sentiment analysis (Groq LLM)
- ✅ Theme tagging: Sound Quality, Battery Life, Comfort/Fit, App Experience, Price/Value, Delivery, Build Quality, ANC
- ✅ Deep action item reports for Product, Marketing & Support teams
- ✅ Beautiful PDF reports
- ✅ Weekly delta detection (only new reviews analyzed)
- ✅ Autonomous AI agent with function calling
- ✅ Conversational querying ("What are top complaints?")
- ✅ Weekly automation via LaunchD (every Sunday 11:59 PM)
- ✅ Flask REST API for external triggers
- ✅ Weekly automation via LaunchD (every Sunday 11:59 PM)
- ✅ Web interface for CSV upload + PDF download

---

## Tech Stack
- **Language**: Python 3.12
- **Database**: SQLite
- **LLM**: Groq API (llama-3.1-8b-instant, llama-3.3-70b-versatile)
- **PDF**: ReportLab
- **Web**: Flask
- **Automation**: LaunchD (Mac native scheduler)
- **Scraping**: BeautifulSoup, Selenium, Playwright, ScraperAPI (see below)

---

## Project Structure
```
voc-agent/
├── data/
│   ├── voc_reviews.db          # SQLite database
│   ├── amazon-review-data.csv  # Kaggle dataset
│   ├── batch1_old.csv          # Pre-2024 reviews (baseline)
│   ├── batch2_new.csv          # 2024 reviews (delta simulation)
│   ├── test_batch1_old.csv     # 150 review test set
│   └── test_batch2_new.csv     # 170 review test set
├── reports/
│   ├── global_report_*.md      # Full product reports
│   ├── weekly_report_*.md      # Delta reports
│   └── voc_report_*.pdf        # PDF reports
├── parser.py                   # CSV → SQLite
├── analyzer.py                 # Groq AI sentiment + themes
├── reporter.py                 # Deep action item reports
├── pdf_generator.py            # ReportLab PDF generation
├── agent.py                    # Function calling AI agent
├── scheduler.py                # Weekly job runner
├── api.py                      # Flask REST API
├── web_app.py                  # Web interface
├── flipkart_scraper.py         # BeautifulSoup scraper (blocked)
├── flipkart_selenium.py        # Selenium scraper (blocked)
├── flipkart_playwright.py      # Playwright scraper (blocked)
├── flipkart_scraperapi.py      # ScraperAPI scraper (blocked)
└── README.md
```

---

## Setup
```bash
pip3 install groq schedule pandas python-dotenv rich reportlab flask beautifulsoup4 requests selenium playwright scraperapi

cp .env.example .env
# Add your GROQ_API_KEY to .env
```

## Usage

### Web Interface (Recommended):
```bash
python3 web_app.py
# Open http://localhost:5002
# Upload CSV → Pipeline runs → Download PDF!
```

### Terminal:
```bash
# Analyze reviews
python3 analyzer.py

# Generate reports
python3 reporter.py

# Generate PDF
python3 pdf_generator.py

# Chat with agent
python3 agent.py

# Weekly job manually
python3 scheduler.py
```

---

## Architecture
```
CSV Upload (Web Interface)
        ↓
parser.py → SQLite DB
        ↓
analyzer.py → Groq AI → Sentiment + Themes
        ↓
reporter.py → Global Report + Weekly Delta Report
        ↓
pdf_generator.py → PDF Report
        ↓
agent.py → Conversational Q&A
        ↓
scheduler.py → Every Sunday auto run
        ↓
api.py → Flask API → n8n Webhook
```

---

## Delta Proof System
Real date-based batch split:

| Batch | Reviews | Represents |
|---|---|---|
| batch1_old.csv | Pre-2024 reviews | Existing scraped database |
| batch2_new.csv | 2024 reviews | This week's new scrape |

Agent automatically detects only NEW reviews on each run — zero duplicates!

---

## Scraping Infrastructure (Research & Development)

Extensive scraping research conducted for Amazon and Flipkart:

### Approaches Attempted:

| Method | Library | Result |
|---|---|---|
| Direct HTTP requests | requests + BeautifulSoup | ❌ 529 Cloudflare block |
| Browser simulation | Selenium + WebDriver | ❌ Bot detection |
| Stealth browser | Playwright + stealth | ❌ JS not rendered |
| Proxy rotation | ScraperAPI | ❌ JS rendering needed |

### Why Scraping is Blocked:
Both Amazon and Flipkart use **Cloudflare Enterprise** protection with:
- Bot fingerprinting
- JavaScript challenges
- IP rate limiting
- Behavioral analysis

### Production Solution:
For production deployment, the following services bypass these protections:
- **BrightData** ($500/month) — residential proxies
- **ScraperAPI Premium** ($49/month) — JS rendering
- **Rainforest API** — Amazon official data partner
- **Flipkart Affiliate API** — official product data

### Current Approach:
**Kaggle dataset** used as industry-standard alternative — same data structure as live scraping. When proxy/API access is available, `parser.py` accepts any CSV in the same format — zero code changes needed!

---

## Data Note
Dataset sourced from Kaggle (Amazon reviews). Products remapped:
- EarFun → Master Buds 1
- Apple AirPods → Master Buds Max

1,411 reviews analyzed across 2 products (2019–2024).

---

## Automation
Weekly automation configured via **Mac LaunchD**:
- Triggers: Every Sunday 11:59 PM
- Detects new reviews automatically
- Generates delta + global reports
- Saves PDF to reports folder

---

## Built With ❤️ for Noise
> "Same infrastructure works with any review source — Amazon, Flipkart, or internal data. Just plug in the CSV!"
