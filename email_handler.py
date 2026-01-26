import os
import smtplib
import imaplib
import email
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

load_dotenv()

class EmailHandler:
    def __init__(self):
        self.email_user = os.getenv("GMAIL_USER")
        self.email_pass = os.getenv("GMAIL_APP_PASSWORD")
        self.imap_server = "imap.gmail.com"

    def get_latest_code(self):
        try:
            print(f"   🔍 Connecting to Gmail as {self.email_user}...")
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_user, self.email_pass)
            mail.select("inbox")

            status, messages = mail.search(None, '(FROM "no-reply@mtmlink.net")')
            
            if not messages[0]:
                print("   ⚠️ No MTM emails found.")
                return None

            latest_email_id = messages[0].split()[-1]
            status, data = mail.fetch(latest_email_id, "(RFC822)")
            
            raw_email = data[0][1]
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
            
            return None
        except Exception as e:
            print(f"   ❌ Error reading email: {e}")
            return None

# UPDATED FUNCTION: Handles 'is_html' and 'to_email'
def send_email(subject, body, attachment_path=None, to_email=None, is_html=False):
    sender_email = os.getenv("GMAIL_USER")
    sender_password = os.getenv("GMAIL_APP_PASSWORD")
    
    if not to_email:
        receiver_email = os.getenv("RECIPIENT_EMAIL", sender_email)
    else:
        receiver_email = to_email

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    # Handle HTML vs Plain Text
    if is_html:
        msg.attach(MIMEText(body, "html"))
    else:
        msg.attach(MIMEText(body, "plain"))

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
        msg.attach(part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"✅ Email sent successfully to {receiver_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
