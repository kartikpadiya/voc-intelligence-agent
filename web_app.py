import os
import json
import threading
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data/'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

job_status = {
    "running": False,
    "step": "",
    "progress": 0,
    "total_steps": 6,
    "log": [],
    "report_ready": False,
    "pdf_path": None,
    "error": None
}

HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VocBot — Voice of Customer Intelligence</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #12121a;
    --border: #1e1e2e;
    --accent: #e94560;
    --accent2: #0f3460;
    --success: #2ecc71;
    --warning: #f39c12;
    --text: #e8e8f0;
    --muted: #6c6c8a;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Mono', monospace;
    min-height: 100vh;
    overflow-x: hidden;
  }

  .noise {
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 0;
  }

  .container {
    max-width: 900px;
    margin: 0 auto;
    padding: 40px 24px;
    position: relative;
    z-index: 1;
  }

  header {
    text-align: center;
    margin-bottom: 60px;
  }

  .logo {
    font-family: 'Syne', sans-serif;
    font-size: 48px;
    font-weight: 800;
    letter-spacing: -2px;
    background: linear-gradient(135deg, #e94560, #0f3460);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
  }

  .tagline {
    color: var(--muted);
    font-size: 13px;
    letter-spacing: 3px;
    text-transform: uppercase;
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px;
    margin-bottom: 24px;
  }

  .card-title {
    font-family: 'Syne', sans-serif;
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 20px;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .badge {
    background: var(--accent);
    color: white;
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 20px;
    letter-spacing: 1px;
  }

  .upload-zone {
    border: 2px dashed var(--border);
    border-radius: 12px;
    padding: 48px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    position: relative;
  }

  .upload-zone:hover, .upload-zone.dragover {
    border-color: var(--accent);
    background: rgba(233, 69, 96, 0.05);
  }

  .upload-icon {
    font-size: 48px;
    margin-bottom: 16px;
    display: block;
  }

  .upload-text {
    font-size: 14px;
    color: var(--muted);
    margin-bottom: 8px;
  }

  .upload-hint {
    font-size: 11px;
    color: var(--muted);
    opacity: 0.6;
  }

  #fileInput { display: none; }

  .file-selected {
    background: rgba(46, 204, 113, 0.1);
    border: 1px solid var(--success);
    border-radius: 8px;
    padding: 12px 16px;
    margin-top: 16px;
    font-size: 13px;
    color: var(--success);
    display: none;
  }

  .btn {
    background: var(--accent);
    color: white;
    border: none;
    padding: 14px 32px;
    border-radius: 8px;
    font-family: 'Syne', sans-serif;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
    width: 100%;
    margin-top: 20px;
    transition: all 0.2s ease;
    letter-spacing: 1px;
  }

  .btn:hover { background: #c73652; transform: translateY(-1px); }
  .btn:disabled { background: var(--border); cursor: not-allowed; transform: none; }

  .btn-secondary {
    background: var(--accent2);
    margin-top: 10px;
  }

  .btn-secondary:hover { background: #0a2a4a; }

  .progress-section { display: none; }

  .steps {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 24px;
  }

  .step {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 8px;
    border: 1px solid var(--border);
    font-size: 13px;
    transition: all 0.3s ease;
  }

  .step.active {
    border-color: var(--warning);
    background: rgba(243, 156, 18, 0.08);
    color: var(--warning);
  }

  .step.done {
    border-color: var(--success);
    background: rgba(46, 204, 113, 0.08);
    color: var(--success);
  }

  .step.pending { color: var(--muted); }

  .step-icon { font-size: 18px; width: 24px; text-align: center; }

  .progress-bar-wrap {
    background: var(--border);
    border-radius: 100px;
    height: 6px;
    overflow: hidden;
    margin-bottom: 8px;
  }

  .progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    border-radius: 100px;
    transition: width 0.5s ease;
    width: 0%;
  }

  .progress-text {
    font-size: 12px;
    color: var(--muted);
    text-align: right;
  }

  .log-box {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    height: 180px;
    overflow-y: auto;
    font-size: 12px;
    color: var(--muted);
    line-height: 1.8;
  }

  .log-box .log-line { color: var(--text); }
  .log-box .log-success { color: var(--success); }
  .log-box .log-error { color: var(--accent); }

  .result-section { display: none; }

  .result-card {
    background: linear-gradient(135deg, rgba(233,69,96,0.15), rgba(15,52,96,0.15));
    border: 1px solid var(--accent);
    border-radius: 16px;
    padding: 32px;
    text-align: center;
  }

  .result-icon { font-size: 64px; margin-bottom: 16px; }

  .result-title {
    font-family: 'Syne', sans-serif;
    font-size: 24px;
    font-weight: 800;
    margin-bottom: 8px;
  }

  .result-sub {
    color: var(--muted);
    font-size: 13px;
    margin-bottom: 24px;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 24px;
  }

  .stat-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    text-align: center;
  }

  .stat-value {
    font-family: 'Syne', sans-serif;
    font-size: 28px;
    font-weight: 800;
    color: var(--accent);
  }

  .stat-label {
    font-size: 10px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
  }

  .chat-section {
    margin-top: 24px;
  }

  .chat-input-wrap {
    display: flex;
    gap: 10px;
    margin-top: 16px;
  }

  .chat-input {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 16px;
    color: var(--text);
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    outline: none;
    transition: border-color 0.2s;
  }

  .chat-input:focus { border-color: var(--accent); }

  .chat-btn {
    background: var(--accent);
    border: none;
    border-radius: 8px;
    padding: 12px 20px;
    color: white;
    cursor: pointer;
    font-size: 18px;
    transition: background 0.2s;
  }

  .chat-btn:hover { background: #c73652; }

  .chat-messages {
    margin-top: 16px;
    max-height: 300px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .msg {
    padding: 12px 16px;
    border-radius: 10px;
    font-size: 13px;
    line-height: 1.7;
    max-width: 85%;
  }

  .msg-user {
    background: rgba(233, 69, 96, 0.15);
    border: 1px solid rgba(233, 69, 96, 0.3);
    align-self: flex-end;
    color: var(--text);
  }

  .msg-bot {
    background: var(--surface);
    border: 1px solid var(--border);
    align-self: flex-start;
    color: var(--text);
  }

  .spinner {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    vertical-align: middle;
    margin-right: 8px;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .pulse {
    animation: pulse 2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
</style>
</head>
<body>
<div class="noise"></div>
<div class="container">

  <header>
    <div class="logo">VocBot</div>
    <div class="tagline">Voice of Customer Intelligence Agent</div>
  </header>

  <!-- Upload Section -->
  <div class="card" id="uploadSection">
    <div class="card-title">
      📁 Upload Reviews CSV
      <span class="badge">STEP 1</span>
    </div>

    <div class="upload-zone" id="uploadZone" onclick="document.getElementById('fileInput').click()">
      <span class="upload-icon">📊</span>
      <div class="upload-text">Drop your CSV file here or click to browse</div>
      <div class="upload-hint">Supports Amazon review CSV format • Max 50MB</div>
      <input type="file" id="fileInput" accept=".csv">
    </div>

    <div class="file-selected" id="fileSelected">
      ✅ <span id="fileName"></span> selected
    </div>

    <button class="btn" id="runBtn" disabled onclick="startPipeline()">
      🚀 Run Intelligence Pipeline
    </button>
  </div>

  <!-- Progress Section -->
  <div class="card progress-section" id="progressSection">
    <div class="card-title">
      <span class="spinner"></span>
      Pipeline Running...
    </div>

    <div class="steps">
      <div class="step pending" id="step1"><span class="step-icon">📥</span> Parsing & cleaning CSV data</div>
      <div class="step pending" id="step2"><span class="step-icon">🗄️</span> Loading into database</div>
      <div class="step pending" id="step3"><span class="step-icon">🧠</span> AI sentiment analysis</div>
      <div class="step pending" id="step4"><span class="step-icon">📝</span> Generating action reports</div>
      <div class="step pending" id="step5"><span class="step-icon">📄</span> Creating PDF report</div>
      <div class="step pending" id="step6"><span class="step-icon">✅</span> Complete!</div>
    </div>

    <div class="progress-bar-wrap">
      <div class="progress-bar" id="progressBar"></div>
    </div>
    <div class="progress-text" id="progressText">0%</div>

    <div class="log-box" id="logBox"></div>
  </div>

  <!-- Result Section -->
  <div class="card result-section" id="resultSection">
    <div class="result-card">
      <div class="result-icon">🎉</div>
      <div class="result-title">Analysis Complete!</div>
      <div class="result-sub">Your VoC intelligence report is ready</div>

      <div class="stats-grid" id="statsGrid"></div>

      <button class="btn" onclick="downloadPDF()">
        📥 Download PDF Report
      </button>
      <button class="btn btn-secondary" onclick="resetUpload()">
        🔄 Analyze Another CSV
      </button>
    </div>
  </div>

  <!-- Chat Section -->
  <div class="card chat-section" id="chatSection" style="display:none">
    <div class="card-title">
      💬 Ask VocBot
      <span class="badge">AI AGENT</span>
    </div>
    <div class="chat-messages" id="chatMessages"></div>
    <div class="chat-input-wrap">
      <input class="chat-input" id="chatInput" placeholder="What are top complaints about Master Buds 1?" onkeypress="if(event.key==='Enter') sendChat()">
      <button class="chat-btn" onclick="sendChat()">→</button>
    </div>
  </div>

</div>

<script>
let selectedFile = null;
let pollInterval = null;

// Drag and drop
const zone = document.getElementById('uploadZone');
zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
zone.addEventListener('drop', e => {
  e.preventDefault();
  zone.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file && file.name.endsWith('.csv')) selectFile(file);
});

document.getElementById('fileInput').addEventListener('change', e => {
  if (e.target.files[0]) selectFile(e.target.files[0]);
});

function selectFile(file) {
  selectedFile = file;
  document.getElementById('fileName').textContent = file.name;
  document.getElementById('fileSelected').style.display = 'block';
  document.getElementById('runBtn').disabled = false;
}

async function startPipeline() {
  if (!selectedFile) return;

  document.getElementById('uploadSection').style.display = 'none';
  document.getElementById('progressSection').style.display = 'block';

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const res = await fetch('/upload-and-run', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.status === 'started') {
      pollInterval = setInterval(pollStatus, 2000);
    }
  } catch (err) {
    addLog('Error starting pipeline: ' + err, 'error');
  }
}

async function pollStatus() {
  try {
    const res = await fetch('/pipeline-status');
    const data = await res.json();

    updateProgress(data);

    if (!data.running && data.report_ready) {
      clearInterval(pollInterval);
      showResults(data);
    } else if (!data.running && data.error) {
      clearInterval(pollInterval);
      addLog('Error: ' + data.error, 'error');
    }
  } catch (err) {
    console.error(err);
  }
}

function updateProgress(data) {
  const pct = Math.round((data.progress / data.total_steps) * 100);
  document.getElementById('progressBar').style.width = pct + '%';
  document.getElementById('progressText').textContent = pct + '%';

  for (let i = 1; i <= 6; i++) {
    const el = document.getElementById('step' + i);
    if (i < data.progress) {
      el.className = 'step done';
    } else if (i === data.progress) {
      el.className = 'step active';
    } else {
      el.className = 'step pending';
    }
  }

  if (data.log && data.log.length > 0) {
    const logBox = document.getElementById('logBox');
    logBox.innerHTML = data.log.map(l => `<div class="log-line">${l}</div>`).join('');
    logBox.scrollTop = logBox.scrollHeight;
  }
}

function addLog(msg, type = 'line') {
  const logBox = document.getElementById('logBox');
  logBox.innerHTML += `<div class="log-${type}">${msg}</div>`;
  logBox.scrollTop = logBox.scrollHeight;
}

async function showResults(data) {
  document.getElementById('progressSection').style.display = 'none';
  document.getElementById('resultSection').style.display = 'block';
  document.getElementById('chatSection').style.display = 'block';

  try {
    const res = await fetch('/stats');
    const stats = await res.json();
    const grid = document.getElementById('statsGrid');
    grid.innerHTML = `
      <div class="stat-box">
        <div class="stat-value">${stats.total}</div>
        <div class="stat-label">Total Reviews</div>
      </div>
      <div class="stat-box">
        <div class="stat-value">${stats.analyzed}</div>
        <div class="stat-label">Analyzed</div>
      </div>
      <div class="stat-box">
        <div class="stat-value">${stats.products}</div>
        <div class="stat-label">Products</div>
      </div>
    `;
  } catch(e) {}
}

function downloadPDF() {
  window.location.href = '/download-pdf';
}

function resetUpload() {
  selectedFile = null;
  document.getElementById('uploadSection').style.display = 'block';
  document.getElementById('resultSection').style.display = 'none';
  document.getElementById('chatSection').style.display = 'none';
  document.getElementById('fileSelected').style.display = 'none';
  document.getElementById('runBtn').disabled = true;
  document.getElementById('fileInput').value = '';
}

async function sendChat() {
  const input = document.getElementById('chatInput');
  const question = input.value.trim();
  if (!question) return;

  const messages = document.getElementById('chatMessages');
  messages.innerHTML += `<div class="msg msg-user">${question}</div>`;
  input.value = '';
  messages.scrollTop = messages.scrollHeight;

  messages.innerHTML += `<div class="msg msg-bot" id="typing"><span class="spinner"></span> Thinking...</div>`;

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question})
    });
    const data = await res.json();
    document.getElementById('typing').remove();
    messages.innerHTML += `<div class="msg msg-bot">${data.answer}</div>`;
    messages.scrollTop = messages.scrollHeight;
  } catch(e) {
    document.getElementById('typing').remove();
    messages.innerHTML += `<div class="msg msg-bot">Error getting answer.</div>`;
  }
}
</script>
</body>
</html>
'''


def run_pipeline_job(csv_path):
    global job_status
    job_status["running"] = True
    job_status["error"] = None
    job_status["report_ready"] = False
    job_status["log"] = []

    def log(msg):
        print(msg)
        job_status["log"].append(msg)

    try:
        # Step 1: Parse CSV
        job_status["step"] = "Parsing CSV"
        job_status["progress"] = 1
        log(f"📥 Parsing CSV: {csv_path}")

        import shutil
        dest = 'data/amazon-review-data.csv'
        if os.path.abspath(csv_path) != os.path.abspath(dest):
            shutil.copy(csv_path, dest)

        from database import init_database
        init_database()
        log("✅ Database initialized")

        # Step 2: Load data
        job_status["step"] = "Loading data"
        job_status["progress"] = 2
        log("🗄️ Loading reviews into database...")

        from parser import parse_and_load
        parse_and_load()
        log("✅ Data loaded successfully")

        # Step 3: Analyze
        job_status["step"] = "Analyzing"
        job_status["progress"] = 3
        log("🧠 Running AI sentiment analysis...")
        log("⏳ This may take a while (rate limits apply)...")

        from analyzer import analyze_all_reviews
        analyze_all_reviews()
        log("✅ Analysis complete")

        # Step 4: Generate reports
        job_status["step"] = "Generating reports"
        job_status["progress"] = 4
        log("📝 Generating action item reports...")

        from reporter import generate_global_report, generate_weekly_report
        import sqlite3
        from database import DB_PATH

        # Check if there are old reviews (delta scenario)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM reviews WHERE week_added = '2025-W01'")
        old_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM reviews WHERE week_added != '2025-W01'")
        new_count = cursor.fetchone()[0]
        conn.close()

        log(f"📊 Old reviews: {old_count} | New reviews: {new_count}")

        # Always generate global report
        log("📝 Generating Global Report...")
        generate_global_report()
        log("✅ Global report done!")

        # Always generate weekly report
        log("📝 Generating Weekly Delta Report...")
        generate_weekly_report()
        if new_count > 0:
            log(f"✅ Weekly delta report done! ({new_count} new reviews detected)")
        else:
            log("✅ Weekly report done!")

        # Step 5: Generate PDF
        job_status["step"] = "Generating PDF"
        job_status["progress"] = 5
        log("📄 Creating beautiful PDF report...")

        from generate_pdf_report import generate_full_pdf as generate_pdf
        pdf_path = generate_pdf()
        job_status["pdf_path"] = pdf_path
        log(f"✅ PDF saved: {pdf_path}")

        # Done!
        job_status["progress"] = 6
        job_status["report_ready"] = True
        log("🎉 Pipeline complete! Reports ready.")

    except Exception as e:
        import traceback
        job_status["error"] = str(e)
        log(f"❌ Error: {str(e)}")
        traceback.print_exc()
    finally:
        job_status["running"] = False


@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/upload-and-run', methods=['POST'])
def upload_and_run():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file"})

    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({"status": "error", "message": "CSV only"})

    filename = secure_filename(file.filename)
    filepath = os.path.join('data', filename)
    file.save(filepath)

    thread = threading.Thread(
        target=run_pipeline_job, args=(filepath,), daemon=True
    )
    thread.start()

    return jsonify({"status": "started"})


@app.route('/pipeline-status')
def pipeline_status():
    return jsonify(job_status)


@app.route('/stats')
def stats():
    try:
        from database import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM reviews')
        total = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM reviews WHERE sentiment IS NOT NULL')
        analyzed = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(DISTINCT product_id) FROM reviews')
        products = cursor.fetchone()[0]
        conn.close()
        return jsonify({
            "total": total,
            "analyzed": analyzed,
            "products": products
        })
    except:
        return jsonify({"total": 0, "analyzed": 0, "products": 0})


@app.route('/download-pdf')
def download_pdf():
    pdf_path = job_status.get("pdf_path")
    if pdf_path and os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True)

    # Find latest PDF
    reports_dir = 'reports'
    if os.path.exists(reports_dir):
        pdfs = [f for f in os.listdir(reports_dir) if f.endswith('.pdf')]
        if pdfs:
            latest = sorted(pdfs)[-1]
            return send_file(
                os.path.join(reports_dir, latest),
                as_attachment=True
            )
    return jsonify({"error": "No PDF found"}), 404


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question', '')
    if not question:
        return jsonify({"answer": "Please ask a question!"})

    try:
        from analyzer import answer_question
        answer = answer_question(question)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"answer": f"Error: {str(e)}"})


if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    print("="*50)
    print("VocBot Web Interface Starting...")
    print("Open: http://localhost:5002")
    print("="*50)
    app.run(host='0.0.0.0', port=5002, debug=False)
