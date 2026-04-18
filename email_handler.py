import smtplib
import os
import imaplib
import email
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

load_dotenv()

# --- 🔧 CREDENTIAL LOADING (Roboust) ---
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_APP_PASS")

if not GMAIL_USER or not GMAIL_PASS:
    print("❌ CRITICAL ERROR: Google Credentials not found in .env file.")
    print("   Please ensure 'GMAIL_USER' and 'GMAIL_APP_PASS' are set.")

def send_email(subject, body, to_email=None, is_html=False, attachment_path=None):
    if not GMAIL_USER or not GMAIL_PASS:
        print("   ⛔ Email skipped: Missing credentials.")
        return

    # Fallback if specific recipient not provided
    if to_email is None:
        to_email = os.getenv("RECIPIENT_EMAIL", GMAIL_USER)

    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = to_email
    msg['Subject'] = subject

    # Attach Body
    msg.attach(MIMEText(body, 'html' if is_html else 'plain'))

    # Attach File (If provided)
    if attachment_path and os.path.exists(attachment_path):
        try:
            filename = os.path.basename(attachment_path)
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {filename}",
            )
            msg.attach(part)
            print(f"   📎 Attached: {filename}")
        except Exception as e:
            print(f"   ⚠️ Attachment Error: {e}")

    try:
        # Connect to Gmail SMTP
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)
        server.quit()
        print(f"   ✅ Email sent successfully to {to_email}")
    except Exception as e:
        print(f"   ❌ Failed to send email: {e}")

class EmailHandler:
    def __init__(self):
        self.email_user = GMAIL_USER
        self.email_pass = GMAIL_PASS
        self.imap_server = "imap.gmail.com"

    def get_latest_code(self):
        """Retrieves the latest MFA code from Gmail (Inbox or Spam)"""
        if not self.email_user or not self.email_pass:
            return None
            
        try:
            print(f"   🔍 Connecting to Gmail as {self.email_user}...")
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_user, self.email_pass)
            
            # 1. Search INBOX
            mail.select("inbox")
            status, messages = mail.search(None, '(FROM "no-reply@mtmlink.net")')
            ids = messages[0].split()
            
            # 2. If not in Inbox, search SPAM
            if not ids:
                print("      🔎 Checking Spam folder...")
                mail.select("[Gmail]/Spam")
                status, messages = mail.search(None, '(FROM "no-reply@mtmlink.net")')
                ids = messages[0].split()

            if ids:
                latest_id = ids[-1]
                _, msg_data = mail.fetch(latest_id, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                body = ""
                
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()
                
                match = re.search(r'\b\d{6}\b', body)
                if match:
                    return match.group(0)
            
            print("   ⚠️ No MTM code found.")
            return None

        except Exception as e:
            print(f"      ⚠️ Email Read Error: {e}")
        return None