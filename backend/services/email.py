"""
Email service using Resend HTTP API (replaces Gmail SMTP — blocked on Render free tier).
"""

import os
import re
import base64
import logging
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

log = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "NutriVeda <onboarding@resend.dev>")


def _plan_to_html(plan_text: str) -> str:
    """Convert markdown plan text to simple HTML for email body."""
    safe = plan_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe = re.sub(r'^### (.+)$', r'<h4 style="color:#16a34a;margin:10px 0 2px">\1</h4>', safe, flags=re.MULTILINE)
    safe = re.sub(r'^## (.+)$', r'<h3 style="color:#fff;background:#16a34a;padding:6px 10px;border-radius:4px;margin:14px 0 2px">\1</h3>', safe, flags=re.MULTILINE)
    safe = re.sub(r'^# (.+)$', r'<h2 style="color:#065f46;margin:0 0 6px">\1</h2>', safe, flags=re.MULTILINE)
    safe = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', safe)
    safe = safe.replace("\n", "<br>")
    return f'<div style="margin:24px 0;padding:16px;background:#f9fafb;border-radius:8px;font-size:13px;line-height:1.7;font-family:monospace;overflow-x:auto;">{safe}</div>'


def send_diet_plan_email(
    to_email: str,
    client_name: str,
    pdf_path: str,
    nutritionist_notes: str = "",
    plan_text: str = "",
) -> bool:
    """Send the approved diet plan to the client via Resend API."""
    if not RESEND_API_KEY:
        log.error("RESEND_API_KEY not set")
        return False

    notes_section = f"""
    <div style="background:#f0fdf4;border-left:4px solid #16a34a;padding:16px;margin:20px 0;border-radius:4px;">
        <p style="margin:0;font-weight:600;color:#15803d;">Personal Note from your Nutritionist:</p>
        <p style="margin:8px 0 0 0;color:#1a1a1a;">{nutritionist_notes}</p>
    </div>""" if nutritionist_notes else ""

    plan_section = _plan_to_html(plan_text) if plan_text else ""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1a1a1a;max-width:700px;margin:0 auto;padding:20px;">

<div style="background:linear-gradient(135deg,#16a34a 0%,#15803d 100%);padding:32px;border-radius:12px;text-align:center;margin-bottom:24px;">
  <h1 style="color:white;margin:0;font-size:24px;">NutriVeda — Your Plan is Ready!</h1>
  <p style="color:#dcfce7;margin:8px 0 0;font-size:14px;">Your Personalised Nutrition Plan has been approved by your nutritionist</p>
</div>

<p style="font-size:16px;">Dear <strong>{client_name}</strong>,</p>
<p>Your personalized diet and fitness plan is ready. It has been crafted specifically for your goals, health profile, and lifestyle.</p>

{notes_section}

<div style="background:#f9fafb;border-radius:8px;padding:20px;margin:20px 0;">
  <h3 style="color:#16a34a;margin-top:0;">What's Inside Your Plan:</h3>
  <ul style="padding-left:20px;line-height:2;">
    <li>Your BMR, TDEE, and personalized calorie targets</li>
    <li>Complete weekly meal plan (Mon–Sun) with exact portions</li>
    <li>Calorie and macro breakdown per meal</li>
    <li>Custom exercise schedule</li>
    <li>Food guide, daily habits, and hydration targets</li>
  </ul>
</div>

{plan_section}

<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:16px;margin:20px 0;">
  <p style="margin:0;font-size:13px;color:#92400e;">
    <strong>Important:</strong> This plan is personalized for you only. Follow it consistently for best results.
    If you experience any discomfort, please reach out immediately.
  </p>
</div>

<p>Stay committed and stay healthy,<br>
<strong>Your Certified Nutrition Consultant</strong><br>
<span style="color:#16a34a;font-weight:600;">NutriVeda</span></p>

<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
<p style="font-size:11px;color:#9ca3af;text-align:center;">
  NutriVeda Nutrition Consultation<br>
  This email is confidential and intended solely for {client_name}.
</p>
</body></html>"""

    # Build Resend payload
    payload: dict = {
        "from": FROM_EMAIL,
        "to": [to_email],
        "subject": f"Your Personalized Diet & Fitness Plan — {client_name}",
        "html": html,
    }

    # Attach PDF if available
    pdf_file = Path(pdf_path) if pdf_path else None
    if pdf_file and pdf_file.exists():
        try:
            with open(pdf_file, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode()
            payload["attachments"] = [{
                "filename": f"NutriVeda_Plan_{client_name.replace(' ', '_')}.pdf",
                "content": pdf_b64,
            }]
            log.info(f"PDF attached: {pdf_file.name}")
        except Exception as e:
            log.warning(f"Could not attach PDF: {e} — sending without attachment")
    else:
        log.info("No PDF — sending plan as email body only")

    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if resp.status_code in (200, 201):
            log.info(f"Email sent via Resend to {to_email} — id={resp.json().get('id')}")
            return True
        else:
            log.error(f"Resend API error {resp.status_code}: {resp.text}")
            raise RuntimeError(f"Resend {resp.status_code}: {resp.text}")
    except httpx.RequestError as e:
        log.error(f"Resend request failed: {e}")
        raise RuntimeError(f"Resend request error: {e}")
