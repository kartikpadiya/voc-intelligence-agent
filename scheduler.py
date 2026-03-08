import os
import sys
from datetime import datetime

os.chdir('/Users/kartik/Desktop/voc-agent')
sys.path.insert(0, '/Users/kartik/Desktop/voc-agent')

print("="*50)
print(f"VOC WEEKLY JOB STARTED: {datetime.now()}")
print("="*50)

try:
    from analyzer import analyze_weekly_reviews
    from reporter import generate_global_report, generate_weekly_report
    from generate_pdf_report import generate_full_pdf as generate_pdf
    from database import get_stats, log_run

    stats_before = get_stats()
    print(f"Reviews before: {stats_before['total']}")

    print("Analyzing new reviews...")
    analyze_weekly_reviews()

    stats_after = get_stats()
    print(f"Reviews after: {stats_after['total']}")

    print("Generating weekly report...")
    generate_weekly_report()

    print("Generating global report...")
    generate_global_report()

    print("Generating PDF...")
    generate_pdf()

    print(f"WEEKLY JOB COMPLETE: {datetime.now()}")
    log_run("weekly", stats_after['total'], "Success")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
