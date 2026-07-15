import os
import sys
import base64
import json
import urllib.request
import urllib.parse
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, render_template_string, flash

# Import process_pdf module directly
import process_pdf

app = Flask(__name__)
app.secret_key = os.urllib.urandom(24) if hasattr(os, "urllib") else "delivery_route_secret_key"

# Configuration defaults
DEFAULT_REPO_URL = "https://github.com/stephend-csu/newspaper-app"

# Beautiful HTML page template using premium Vanilla CSS (Glassmorphism, dark/light theme, custom animations)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Delivery Route Customizer</title>
    <link rel="icon" type="image/png" href="/favicon.png">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.8.1/css/all.css">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            --panel-bg: rgba(255, 255, 255, 0.08);
            --panel-border: rgba(255, 255, 255, 0.12);
            --accent-color: #6366f1;
            --accent-hover: #4f46e5;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --shadow-primary: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-gradient);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            overflow-x: hidden;
        }

        /* Ambient floating circles for premium design depth */
        .ambient-glow {
            position: absolute;
            width: 400px;
            height: 400px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, rgba(99, 102, 241, 0) 70%);
            z-index: -1;
            filter: blur(40px);
            pointer-events: none;
        }

        .ambient-1 {
            top: 10%;
            left: 10%;
        }

        .ambient-2 {
            bottom: 10%;
            right: 10%;
            background: radial-gradient(circle, rgba(236, 72, 153, 0.1) 0%, rgba(236, 72, 153, 0) 70%);
        }

        .container {
            width: 100%;
            max-width: 540px;
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-radius: 24px;
            padding: 40px;
            box-shadow: var(--shadow-primary);
            animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        header {
            text-align: center;
            margin-bottom: 35px;
        }

        .logo-icon {
            font-size: 2.8em;
            color: var(--accent-color);
            margin-bottom: 12px;
            display: inline-block;
            filter: drop-shadow(0 0 10px rgba(99, 102, 241, 0.4));
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-8px); }
        }

        h1 {
            font-weight: 800;
            font-size: 1.8em;
            letter-spacing: -0.5px;
            margin-bottom: 8px;
            background: linear-gradient(to right, #ffffff, #c7d2fe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        p.subtitle {
            color: var(--text-muted);
            font-size: 0.95em;
            line-height: 1.5;
        }

        .form-group {
            margin-bottom: 24px;
        }

        label {
            display: block;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-bottom: 8px;
        }

        .input-wrapper {
            position: relative;
            display: flex;
            align-items: center;
        }

        .input-icon {
            position: absolute;
            left: 16px;
            color: var(--text-muted);
            font-size: 1.1em;
            pointer-events: none;
            transition: color 0.3s ease;
        }

        input[type="email"], input[type="text"] {
            width: 100%;
            padding: 14px 16px 14px 44px;
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--panel-border);
            border-radius: 12px;
            font-family: inherit;
            color: var(--text-main);
            font-size: 0.95em;
            outline: none;
            transition: all 0.3s ease;
        }

        input[type="email"]:focus, input[type="text"]:focus {
            border-color: var(--accent-color);
            background: rgba(15, 23, 42, 0.7);
            box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.15);
        }

        input[type="email"]:focus + .input-icon {
            color: var(--accent-color);
        }

        /* File Upload Styling */
        .file-upload-area {
            border: 2px dashed var(--panel-border);
            border-radius: 16px;
            padding: 30px 20px;
            text-align: center;
            cursor: pointer;
            background: rgba(255, 255, 255, 0.02);
            transition: all 0.3s ease;
            position: relative;
        }

        .file-upload-area:hover, .file-upload-area.dragover {
            border-color: var(--accent-color);
            background: rgba(99, 102, 241, 0.04);
        }

        .file-upload-area input[type="file"] {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            opacity: 0;
            cursor: pointer;
        }

        .upload-icon {
            font-size: 2.2em;
            color: var(--text-muted);
            margin-bottom: 12px;
            transition: color 0.3s ease;
        }

        .file-upload-area:hover .upload-icon {
            color: var(--accent-color);
        }

        .upload-text {
            font-size: 0.95em;
            color: var(--text-main);
            margin-bottom: 4px;
        }

        .upload-hint {
            font-size: 0.8em;
            color: var(--text-muted);
        }

        .file-selected-name {
            margin-top: 10px;
            font-size: 0.9em;
            color: var(--accent-color);
            font-weight: 600;
            display: none;
        }

        .btn-submit {
            width: 100%;
            padding: 16px;
            background: var(--accent-color);
            border: none;
            border-radius: 12px;
            font-family: inherit;
            color: white;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
            margin-top: 30px;
        }

        .btn-submit:hover {
            background: var(--accent-hover);
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
        }

        .btn-submit:active {
            transform: translateY(0);
        }

        /* Alert styling */
        .alerts {
            margin-bottom: 24px;
        }

        .alert {
            padding: 14px 16px;
            border-radius: 12px;
            font-size: 0.9em;
            line-height: 1.5;
            margin-bottom: 12px;
            display: flex;
            align-items: flex-start;
            gap: 10px;
            border: 1px solid transparent;
        }

        .alert-success {
            background-color: rgba(16, 185, 129, 0.1);
            border-color: rgba(16, 185, 129, 0.2);
            color: #34d399;
        }

        .alert-error {
            background-color: rgba(239, 68, 68, 0.1);
            border-color: rgba(239, 68, 68, 0.2);
            color: #f87171;
        }

        .alert-info {
            background-color: rgba(59, 130, 246, 0.1);
            border-color: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
        }

        /* Loading Overlay overlay */
        .loading-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(8px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            gap: 20px;
        }

        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(255, 255, 255, 0.1);
            border-top-color: var(--accent-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .loading-text {
            font-size: 1.1em;
            font-weight: 600;
            letter-spacing: 0.5px;
            color: var(--text-main);
        }

        .loading-subtext {
            font-size: 0.85em;
            color: var(--text-muted);
        }
    </style>
</head>
<body>
    <div class="ambient-glow ambient-1"></div>
    <div class="ambient-glow ambient-2"></div>

    <div class="container">
        <header>
            <span class="logo-icon"><i class="fas fa-route"></i></span>
            <h1>Route Dispatcher</h1>
            <p class="subtitle">Upload your delivery PDF to automatically update, geocode, optimize, and publish the route list.</p>
        </header>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <div class="alerts">
              {% for category, message in messages %}
                <div class="alert alert-{{ category }}">
                  <i class="fas {% if category == 'success' %}fa-check-circle{% elif category == 'error' %}fa-exclamation-circle{% else %}fa-info-circle{% endif %}"></i>
                  <div>{{ message|safe }}</div>
                </div>
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}

        <form method="POST" enctype="multipart/form-data" id="uploadForm">
            <div class="form-group">
                <label>PDF Delivery File</label>
                <div class="file-upload-area" id="dropArea">
                    <span class="upload-icon"><i class="fas fa-file-pdf"></i></span>
                    <div class="upload-text">Choose file or drag here</div>
                    <div class="upload-hint">Only PDF files generated by District Net</div>
                    <input type="file" name="pdf_file" accept=".pdf" required id="fileInput">
                    <div class="file-selected-name" id="fileName">Selected: route.pdf</div>
                </div>
            </div>

            <div class="form-group">
                <label>Notification Email</label>
                <div class="input-wrapper">
                    <input type="email" name="email_address" placeholder="e.g. driver@example.com" required>
                    <span class="input-icon"><i class="fas fa-envelope"></i></span>
                </div>
            </div>

            <button type="submit" class="btn-submit">
                <i class="fas fa-paper-plane"></i> Process Route
            </button>
        </form>
    </div>

    <div class="loading-overlay" id="loadingOverlay">
        <div class="spinner"></div>
        <div class="loading-text">Processing Delivery Route...</div>
        <div class="loading-subtext">Geocoding addresses and calculating shortest route (this may take up to a minute)</div>
    </div>

    <script>
        const fileInput = document.getElementById('fileInput');
        const fileName = document.getElementById('fileName');
        const dropArea = document.getElementById('dropArea');
        const uploadForm = document.getElementById('uploadForm');
        const loadingOverlay = document.getElementById('loadingOverlay');

        fileInput.addEventListener('change', (e) => {
            if (fileInput.files.length > 0) {
                fileName.textContent = `Selected: ${fileInput.files[0].name}`;
                fileName.style.display = 'block';
            } else {
                fileName.style.display = 'none';
            }
        });

        // Drag and drop handlers
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropArea.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropArea.classList.remove('dragover');
            }, false);
        });

        // Form submission loading indicator
        uploadForm.addEventListener('submit', () => {
            loadingOverlay.style.display = 'flex';
        });
    </script>
</body>
</html>
"""

def get_github_sha(token, owner, repo, path):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AntigravityDeliveryRouter/1.0"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise e

def push_to_github(token, owner, repo, path, file_bytes):
    sha = get_github_sha(token, owner, repo, path)
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AntigravityDeliveryRouter/1.0",
        "Content-Type": "application/json"
    }
    payload = {
        "message": "Automated delivery route update from PDF upload",
        "content": base64.b64encode(file_bytes).decode("utf-8")
    }
    if sha:
        payload["sha"] = sha
        
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="PUT")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.getcode() == 200 or resp.getcode() == 201

def send_notification_email(recipient_email, github_url):
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    
    if not smtp_user or not smtp_pass:
        print("SMTP credentials missing. Skipping email notification.")
        return False, "SMTP credentials missing"
        
    # Construct pages URL
    # e.g., https://github.com/stephend-csu/newspaper-app -> https://stephend-csu.github.io/newspaper-app/
    pages_url = github_url
    if "github.com/" in github_url:
        parts = github_url.split("github.com/")[1].split("/")
        if len(parts) >= 2:
            owner = parts[0]
            repo = parts[1].replace(".git", "")
            pages_url = f"https://{owner}.github.io/{repo}/"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'New Delivery Route Dispatched'
    msg['From'] = smtp_user
    msg['To'] = recipient_email

    text = f"Hello,\n\nYour new newspaper delivery route has been successfully generated and published!\n\nView the interactive map here:\n{pages_url}\n\nHappy delivering!"
    html = f"""
    <html>
      <head>
        <style>
          body {{ font-family: 'Outfit', sans-serif; background-color: #f8fafc; color: #1e293b; padding: 20px; }}
          .card {{ background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; padding: 30px; max-width: 500px; margin: 0 auto; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
          .title {{ font-size: 1.4em; font-weight: 700; color: #0f172a; margin-bottom: 12px; }}
          .text {{ font-size: 1em; line-height: 1.6; margin-bottom: 24px; color: #475569; }}
          .btn {{ display: inline-block; background-color: #6366f1; color: #ffffff !important; padding: 12px 24px; border-radius: 8px; font-weight: 600; text-decoration: none; text-align: center; }}
          .footer {{ font-size: 0.8em; color: #94a3b8; margin-top: 30px; text-align: center; }}
        </style>
      </head>
      <body>
        <div class="card">
          <div class="title">Route Published! 🗺️</div>
          <div class="text">Your delivery PDF has been processed. The addresses are geocoded, optimized for the shortest route starting from Concord BANG, and published to GitHub.</div>
          <a href="{pages_url}" class="btn">View Interactive Route Map</a>
          <div class="footer">Automated Dispatch System</div>
        </div>
      </body>
    </html>
    """

    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, recipient_email, msg.as_string())
        server.quit()
        return True, None
    except Exception as e:
        print(f"Error sending email: {e}")
        return False, str(e)

def process_and_push_background(pdf_path, email_address, github_token, repo_url):
    try:
        # 2. Run PDF process & route optimization
        process_pdf.main()
        
        # Check Chapters.csv was updated
        chapters_path = os.path.join(os.getcwd(), "csv", "Chapters.csv")
        if not os.path.exists(chapters_path):
            print("Processing completed, but Chapters.csv was not generated.")
            return
            
        # Load the newly written CSV bytes
        with open(chapters_path, "rb") as f:
            csv_bytes = f.read()
            
        # 3. Commit/Push to GitHub
        github_pushed = False
        if github_token and "github.com/" in repo_url:
            parts = repo_url.split("github.com/")[1].split("/")
            if len(parts) >= 2:
                owner = parts[0]
                repo = parts[1].replace(".git", "")
                try:
                    github_pushed = push_to_github(github_token, owner, repo, "csv/Chapters.csv", csv_bytes)
                except Exception as e:
                    print(f"GitHub push failed: {e}")
                    
        # 4. Email Notification
        if github_pushed and email_address:
            send_notification_email(email_address, repo_url)
            
    except Exception as e:
        print(f"Error in background processing: {e}")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        pdf_file = request.files.get("pdf_file")
        email_address = request.form.get("email_address")
        
        if not pdf_file or pdf_file.filename == "":
            flash("Please choose a valid PDF file.", "error")
            return render_template_string(HTML_TEMPLATE)
            
        # 1. Save file locally
        pdf_path = os.path.join(os.getcwd(), "MyDistrictNet.pdf")
        pdf_file.save(pdf_path)
        
        github_token = os.environ.get("GITHUB_TOKEN")
        repo_url = os.environ.get("GITHUB_REPO_URL", DEFAULT_REPO_URL)
        
        # Start background processing to avoid Render's 100-second timeout
        thread = threading.Thread(target=process_and_push_background, args=(pdf_path, email_address, github_token, repo_url))
        thread.daemon = True
        thread.start()
        
        flash("<strong>Processing Started!</strong><br>Your PDF has been received and is being processed in the background. Because geocoding all addresses takes a couple of minutes, this avoids server timeouts. You will receive an email shortly once the route is published to GitHub!", "info")
        
    return render_template_string(HTML_TEMPLATE)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    # Run server on all interfaces (mobile testing)
    app.run(host="0.0.0.0", port=port, debug=True)
