# VOC Intelligence Agent 🎧

An autonomous AI Agent that analyzes Amazon customer reviews for audio products and generates actionable intelligence reports.

## Products Monitored
- **Master Buds 1** (EarFun)
- **Master Buds Max** (Apple AirPods)

## Features
- Automated review scraping (Amazon)
- AI-powered sentiment analysis (Groq LLM)
- Theme tagging: Sound Quality, Battery Life, Comfort/Fit, App Experience, Price/Value, Delivery, Build Quality, ANC
- Deep action item reports for Product, Marketing & Support teams
- Beautiful PDF reports
- Weekly delta detection (only new reviews analyzed)
- Autonomous AI agent with function calling
- Weekly automation via LaunchD + n8n

## Tech Stack
- Python 3.12
- SQLite
- Groq API (llama-3.1-8b-instant, llama-3.3-70b-versatile)
- ReportLab (PDF generation)
- Flask (API)
- n8n (workflow automation)
- LaunchD (Mac scheduler)

## Setup
```bash
pip3 install groq schedule pandas python-dotenv rich reportlab flask
cp .env.example .env
# Add your GROQ_API_KEY to .env
```

## Usage
```bash
# Chat with agent
python3 agent.py

# Generate reports
python3 reporter.py

# Generate PDF
python3 pdf_generator.py

# Run weekly job manually
python3 scheduler.py
```

## Architecture
```
CSV Data → parser.py → SQLite DB → analyzer.py (Groq AI)
→ reporter.py → MD Reports
→ pdf_generator.py → PDF Reports
→ agent.py → Function Calling Agent
→ scheduler.py → Weekly Automation
→ api.py → Flask API → n8n Webhook
```

## Delta Proof
- Pre-2024 reviews = Batch 1 (existing database)
- 2024 reviews = Batch 2 (weekly new scrape simulation)
- Agent detects only new reviews every Sunday

## Note on Scraping
Amazon blocks automated scraping. Real dataset from Kaggle used as industry-standard alternative. Scraping infrastructure ready for when proxy/API access available.
