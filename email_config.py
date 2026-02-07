import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ===== EMAIL CONFIG =====
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')

def send_email_alert(subject, body):
    """Send email alert"""
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = SENDER_EMAIL
        message["To"] = RECIPIENT_EMAIL
        
        # Add HTML body
        html_part = MIMEText(body, "html")
        message.attach(html_part)
        
        # Connect to Gmail and send
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(message)
        
        print("📧 Email alert sent")
        return True
        
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def format_email_alert(url, status_code=None, error=None, stats=None):
    """Format a nice HTML email"""
    if error:
        # Site is DOWN
        subject = f"🚨 ALERT: {url} is DOWN"
        
        body = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }}
                .status {{
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
                .info {{
                    background: #f9fafb;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 10px 0;
                }}
                .label {{
                    color: #6b7280;
                    font-size: 14px;
                    margin-bottom: 5px;
                }}
                .value {{
                    color: #111827;
                    font-size: 16px;
                    font-weight: 600;
                }}
                .footer {{
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                    color: #6b7280;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="status">🚨 Site Down Alert</div>
                    <div>{url}</div>
                </div>
                
                <div class="info">
                    <div class="label">Error:</div>
                    <div class="value">{error}</div>
                </div>
                
                <div class="info">
                    <div class="label">Time:</div>
                    <div class="value">{stats.get('timestamp', 'N/A')}</div>
                </div>
                
                <div class="info">
                    <div class="label">Historical Uptime:</div>
                    <div class="value">{stats.get('uptime', 0):.1f}%</div>
                </div>
                
                <div class="footer">
                    <p>This is an automated alert from your Site Monitor.</p>
                    <p>The monitor will check again in 5 minutes.</p>
                </div>
            </div>
        </body>
        </html>
        """
    else:
        # Site has warning (unusual status code)
        subject = f"⚠️ WARNING: {url} returned status {status_code}"
        
        body = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }}
                .status {{
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
                .info {{
                    background: #f9fafb;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 10px 0;
                }}
                .label {{
                    color: #6b7280;
                    font-size: 14px;
                    margin-bottom: 5px;
                }}
                .value {{
                    color: #111827;
                    font-size: 16px;
                    font-weight: 600;
                }}
                .footer {{
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                    color: #6b7280;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="status">⚠️ Warning Alert</div>
                    <div>{url}</div>
                </div>
                
                <div class="info">
                    <div class="label">Status Code:</div>
                    <div class="value">{status_code}</div>
                </div>
                
                <div class="info">
                    <div class="label">Historical Uptime:</div>
                    <div class="value">{stats.get('uptime', 0):.1f}%</div>
                </div>
                
                <div class="footer">
                    <p>This is not a complete failure, but the site returned an unusual status code.</p>
                    <p>The monitor will continue checking every 5 minutes.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    return subject, body
        </html>
        """
    
    return subject, body
