import asyncio
import schedule
import time
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

from database import init_database, insert_reviews, get_stats, log_run
from analyzer import analyze_all_reviews, analyze_weekly_reviews, answer_question
from reporter import generate_global_report, generate_weekly_report

load_dotenv()

def chat_mode():
    print("="*50)
    print("VOC Agent - Chat Mode")
    print("Type 'exit' to quit")
    print("="*50)

    while True:
        try:
            question = input("\nYour Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting chat mode.")
            break

        if question.lower() == "exit":
            print("Exiting chat mode.")
            break

        if not question:
            continue

        answer_question(question)


def run_weekly_update():
    print("Running Weekly Update...")
    analyze_weekly_reviews()
    generate_global_report()
    generate_weekly_report()


def start_scheduler():
    print("Scheduler started - runs every Sunday at 9:00 AM")
    schedule.every().sunday.at("09:00").do(run_weekly_update)
    while True:
        schedule.run_pending()
        time.sleep(3600)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "chat":
            chat_mode()

        elif command == "report":
            generate_global_report()
            generate_weekly_report()

        elif command == "analyze":
            analyze_all_reviews()

        elif command == "schedule":
            start_scheduler()

        else:
            print(f"Unknown command: {command}")
            print("Usage: python3 main.py [chat|report|analyze|schedule]")
    else:
        print("Usage: python3 main.py [chat|report|analyze|schedule]")
        print("  chat     - Ask questions about reviews")
        print("  report   - Generate reports")
        print("  analyze  - Run AI analysis")
        print("  schedule - Start weekly scheduler")
