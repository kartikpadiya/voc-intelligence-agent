from flask import Flask, jsonify
import subprocess
import threading
import os
from datetime import datetime

app = Flask(__name__)
job_status = {"running": False, "last_run": None, "last_result": "Never run"}

def run_job_background():
    job_status["running"] = True
    job_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        from analyzer import analyze_weekly_reviews
        from reporter import generate_global_report, generate_weekly_report
        from pdf_generator import generate_pdf
        analyze_weekly_reviews()
        generate_weekly_report()
        generate_global_report()
        generate_pdf()
        job_status["last_result"] = "Success"
    except Exception as e:
        job_status["last_result"] = f"Error: {str(e)}"
    finally:
        job_status["running"] = False

@app.route('/run-weekly', methods=['GET'])
def run_weekly():
    if job_status["running"]:
        return jsonify({"status": "already_running"})
    thread = threading.Thread(target=run_job_background)
    thread.daemon = True
    thread.start()
    return jsonify({
        "status": "started",
        "message": "Weekly job started in background!"
    })

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "VOC Agent Running!",
        "job_running": job_status["running"],
        "last_run": job_status["last_run"],
        "last_result": job_status["last_result"]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
