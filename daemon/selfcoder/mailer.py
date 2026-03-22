import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

class Mailer:
    def __init__(self, email="niam-bay@hotmail.com", smtp_server="smtp-mail.outlook.com", smtp_port=587):
        self.email = email
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def format_report(self, completed=None, failed=None, suggestions=None) -> str:
        """Format daily report as plain text email."""
        lines = [f"Rapport Niam-Bay Auto — {datetime.now().strftime('%d %B %Y')}", ""]

        if completed:
            lines.append("COMPLÉTÉES:")
            for t in completed:
                lines.append(f"  ✅ {t['name']} (branche: {t.get('branch','-')})")
                lines.append(f"     Diff: +{t.get('lines',0)} lignes, tests: {t.get('tests','-')}")
            lines.append("")

        if failed:
            lines.append("ABANDONNÉES:")
            for t in failed:
                lines.append(f"  ❌ {t['name']} — {t.get('error','-')}")
                lines.append(f"     Tentatives: {t.get('attempts',0)}")
            lines.append("")

        if suggestions:
            lines.append("SUGGESTIONS:")
            for s in suggestions:
                lines.append(f"  💡 {s}")
            lines.append("")

        lines.append("— Niam-Bay 🤖")
        return "\n".join(lines)

    def send(self, subject: str, body: str) -> bool:
        """Send email via SMTP. Password from env var NIAMBAY_EMAIL_PWD."""
        password = os.environ.get("NIAMBAY_EMAIL_PWD", "")
        if not password:
            return False
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = self.email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Mail error: {e}")
            return False
