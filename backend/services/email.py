"""
Gmail SMTP email service for sending diet plans to clients.
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

log = logging.getLogger(__name__)

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")


def send_diet_plan_email(
    to_email: str,
    client_name: str,
    pdf_path: str,
    nutritionist_notes: str = "",
    plan_text: str = "",
) -> bool:
    """
    Send the approved diet plan PDF to the client via Gmail.

    Args:
        to_email: Client's email address
        client_name: Client's full name
        pdf_path: Absolute path to the PDF file
        nutritionist_notes: Optional personal note from the nutritionist

    Returns:
        True if email sent successfully, False otherwise
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        log.error("Gmail credentials not configured in .env file")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = f"NutriVeda Nutrition Consultant <{GMAIL_USER}>"
        msg["To"] = to_email
        msg["Subject"] = f"Your Personalized Nutrition Plan — {client_name}"

        # HTML email body
        notes_section = f"""
        <div style="background:#f0fdf4;border-left:4px solid #16a34a;padding:16px;margin:20px 0;border-radius:4px;">
            <p style="margin:0;font-weight:600;color:#15803d;">Personal Note from your Nutritionist:</p>
            <p style="margin:8px 0 0 0;color:#1a1a1a;">{nutritionist_notes}</p>
        </div>
        """ if nutritionist_notes else ""

        html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1a1a1a; max-width: 600px; margin: 0 auto; padding: 20px;">

    <div style="background: linear-gradient(135deg, #16a34a 0%, #15803d 100%); padding: 32px; border-radius: 12px; text-align: center; margin-bottom: 24px;">
        <h1 style="color: white; margin: 0; font-size: 24px;">🌿 NutriVeda — Your Plan is Ready!</h1>
        <p style="color: #dcfce7; margin: 8px 0 0 0; font-size: 14px;">Your Personalised 30-Day Nutrition Plan has been approved</p>
    </div>

    <p style="font-size: 16px;">Dear <strong>{client_name}</strong>,</p>

    <p>I'm delighted to share your personalized nutrition plan, crafted specifically for your goals, health profile, and lifestyle.</p>

    {notes_section}

    <div style="background: #f9fafb; border-radius: 8px; padding: 20px; margin: 20px 0;">
        <h3 style="color: #16a34a; margin-top: 0;">📋 What's Inside Your Plan:</h3>
        <ul style="padding-left: 20px; line-height: 2;">
            <li>Your BMR, TDEE, and personalized calorie targets</li>
            <li>Complete 30-day Indian meal plan with exact portions</li>
            <li>Meal timings and preparation tips</li>
            <li>Hydration and supplement recommendations</li>
            <li>Foods to avoid and lifestyle tips</li>
            <li>Progress monitoring schedule</li>
        </ul>
    </div>

    <p><strong>📎 Your plan is attached as a PDF.</strong> Please save it for easy reference.</p>

    <div style="background: #fffbeb; border: 1px solid #fcd34d; border-radius: 8px; padding: 16px; margin: 20px 0;">
        <p style="margin: 0; font-size: 13px; color: #92400e;">
            ⚠️ <strong>Important:</strong> This plan is personalized for you only.
            Follow it consistently for best results. If you experience any discomfort,
            please reach out immediately.
        </p>
    </div>

    <p>Remember, consistency is key. Small daily actions lead to big long-term results.
    I'm here to support you every step of the way!</p>

    <p>Stay committed and stay healthy,<br>
    <strong>Your Certified Nutrition Consultant</strong><br>
    <span style="color:#16a34a;font-weight:600;">NutriVeda</span></p>

    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
    <p style="font-size: 11px; color: #9ca3af; text-align: center;">
        NutriVeda Nutrition Consultation | {GMAIL_USER}<br>
        This email and attachment are confidential and intended solely for {client_name}.
    </p>

</body>
</html>
"""

        # Embed plan text in email body if available
        plan_html = ""
        if plan_text:
            import re as _re
            # Convert markdown to simple HTML for email
            safe_plan = plan_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Headers
            safe_plan = _re.sub(r'^### (.+)$', r'<h4 style="color:#16a34a;margin:12px 0 4px">\1</h4>', safe_plan, flags=_re.MULTILINE)
            safe_plan = _re.sub(r'^## (.+)$', r'<h3 style="color:#065f46;background:#ecfdf5;padding:8px;border-radius:4px;margin:16px 0 4px">\1</h3>', safe_plan, flags=_re.MULTILINE)
            safe_plan = _re.sub(r'^# (.+)$', r'<h2 style="color:#065f46;margin:0 0 8px">\1</h2>', safe_plan, flags=_re.MULTILINE)
            # Bold
            safe_plan = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', safe_plan)
            # Tables → preserve as preformatted
            safe_plan = safe_plan.replace("\n", "<br>")
            plan_html = f"""
            <div style="margin:24px 0;padding:20px;background:#f9fafb;border-radius:8px;font-size:13px;line-height:1.8;font-family:monospace;white-space:pre-wrap;overflow-x:auto;">
                {safe_plan}
            </div>
            """

        msg.attach(MIMEText(html_body + plan_html, "html"))

        # Attach PDF if available
        pdf_file = Path(pdf_path) if pdf_path else None
        if pdf_file and pdf_file.exists():
            with open(pdf_file, "rb") as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                pdf_attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=f"Nutrition_Plan_{client_name.replace(' ', '_')}.pdf"
                )
                msg.attach(pdf_attachment)
            log.info(f"PDF attached: {pdf_file.name}")
        else:
            log.info("No PDF available — sending plan as email body only")

        # Send via Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        log.info(f"Email sent successfully to {to_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        log.error("Gmail authentication failed. Check your App Password in .env")
        return False
    except Exception as e:
        log.error(f"Failed to send email: {e}")
        return False
