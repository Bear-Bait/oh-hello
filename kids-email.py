import smtplib
from email.mime.text import MIMEText
from flask import Flask, request, render_template_string
import os

app = Flask(__name__)

# Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
GMAIL_ADDRESS = "forrestmuelrath@gmail.com"  # Replace with your Gmail
APP_PASSWORD = "hvwk eswt yumm rdbe"      # You'll generate this in Gmail settings

# Simple HTML form template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Send Message to Uncle</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 20px auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        textarea { width: 100%; height: 200px; }
        button { background: #4CAF50; color: white; padding: 10px 20px; border: none; }
    </style>
</head>
<body>
    <h1>Send a Message to Uncle</h1>
    <form method="POST">
        <div class="form-group">
            <label>Subject:</label><br>
            <input type="text" name="subject" required>
        </div>
        <div class="form-group">
            <label>Message:</label><br>
            <textarea name="message" required></textarea>
        </div>
        <button type="submit">Send Message</button>
    </form>
    {% if message %}
        <p>{{ message }}</p>
    {% endif %}
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    status_message = ""
    
    if request.method == 'POST':
        subject = request.form['subject']
        message_body = request.form['message']
        
        try:
            # Create email
            msg = MIMEText(message_body)
            msg['Subject'] = subject
            msg['From'] = "RaspberryPi <local@raspberrypi.local>"
            msg['To'] = GMAIL_ADDRESS
            
            # Send email
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(GMAIL_ADDRESS, APP_PASSWORD)
                server.send_message(msg)
            
            status_message = "Message sent successfully! ✨"
        except Exception as e:
            status_message = f"Error sending message: {str(e)}"
    
    return render_template_string(HTML_TEMPLATE, message=status_message)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
