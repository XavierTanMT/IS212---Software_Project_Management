"""Simple email sending utilities (SMTP)."""
import os

def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send an email using SMTP settings from environment.

    Reads SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD and EMAIL_FROM from env.
    Returns True on success, False otherwise.
    """
    try:
        import smtplib
        from email.message import EmailMessage

        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        email_from = os.getenv("EMAIL_FROM") or smtp_user

        if not smtp_host or not smtp_user or not smtp_password:
            print("SMTP not configured - skipping email send")
            return False

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = email_from
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        # Helpful log for debugging local email sends
        print(f"Email sent to {to_email} via {smtp_host}:{smtp_port} as {smtp_user}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
