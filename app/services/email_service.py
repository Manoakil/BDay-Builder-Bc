import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

async def send_email(to_email: str, subject: str, body: str):
    sender_email = "bdaybuilder@gmail.com"
    password = settings.SMTP_PASSWORD
    
    if not password:
        print(f"Mock email to {to_email} with subject: {subject}")
        print("SMTP_PASSWORD not set in backend .env! Real email will not be sent.")
        return {"status": "error", "message": "SMTP_PASSWORD not configured"}

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print(f"Successfully sent email to {to_email}")
        return {"status": "success", "message": "Email sent"}
    except Exception as e:
        print(f"Failed to send email: {e}")
        return {"status": "error", "message": str(e)}
