# VOC Intelligence Agent 🎧

An autonomous AI agent that scrapes, analyzes, and reports on 
customer reviews for audio/wearable products.

## Setup

### 1. Install Dependencies
pip3 install requests beautifulsoup4 playwright groq 
schedule pandas python-dotenv
playwright install chromium

### 2. Add API Key
Create a .env file and add:
GROQ_API_KEY=your_groq_api_key_here

### 3. Run the Agent

# Full pipeline (scrape + analyze + report)
python3 main.py run

# Chat mode (ask questions)
python3 main.py chat

# Reports only
python3 main.py report

# Start weekly scheduler
python3 main.py schedule

## Project Structure
voc-agent/
├── data/          → Review database and raw JSON files
├── reports/       → Generated markdown reports
├── logs/          → Run logs
├── scraper.py     → Web scraping from Amazon
├── database.py    → SQLite database management
├── analyzer.py    → AI sentiment and theme analysis
├── reporter.py    → Report generation
├── main.py        → Master controller
├── SOUL.md        → Agent identity and personality
└── README.md      → This file

## Products Monitored
- Master Buds 1 (Sony WF-1000XM4)
- Master Buds Max (Apple AirPods Pro 2nd Gen)

## Output Reports
- reports/global_report_YYYYMMDD.md
- reports/weekly_report_YYYY_WXX.md

## Sample Questions for Chat Mode
- What do customers say about battery life?
- Which product has better ANC reviews?
- What are the top complaints for Master Buds 1?
