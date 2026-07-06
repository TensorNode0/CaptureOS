"""Outbound email: Resend API (primary), SMTP (fallback), console mock (dev).

Configuration (env):
  RESEND_API_KEY  — use https://resend.com (simplest; free tier is plenty)
  EMAIL_FROM      — e.g. "CaptureAgent <noreply@captureagent.us>" (domain must
                    be verified with the provider)
  SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS — generic SMTP fallback if no Resend

When neither is configured, emails print to the server log and token links
are surfaced in API responses (local development only). When real email IS
configured, links are sent to the inbox and never included in responses.
"""
import os
import asyncio
import smtplib
from email.mime.text import MIMEText

import httpx


def _from_addr() -> str:
    return os.environ.get("EMAIL_FROM", "CaptureAgent <noreply@captureagent.us>")


def configured() -> bool:
    """True when a real delivery channel is configured."""
    return bool(os.environ.get("RESEND_API_KEY") or os.environ.get("SMTP_HOST"))


def _smtp_send(to: str, subject: str, html: str):
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = _from_addr()
    msg["To"] = to
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.ehlo()
        if os.environ.get("SMTP_TLS", "1") != "0":
            s.starttls()
        user = os.environ.get("SMTP_USER")
        if user:
            s.login(user, os.environ.get("SMTP_PASS", ""))
        s.send_message(msg)


async def send(to: str, subject: str, html: str):
    """Send an email; raises on delivery failure so callers can surface it."""
    resend_key = os.environ.get("RESEND_API_KEY")
    if resend_key:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}"},
                json={"from": _from_addr(), "to": [to],
                      "subject": subject, "html": html})
            if r.status_code >= 300:
                raise RuntimeError(f"Resend rejected the email ({r.status_code}): {r.text[:300]}")
        return
    if os.environ.get("SMTP_HOST"):
        await asyncio.to_thread(_smtp_send, to, subject, html)
        return
    print(f"[EMAIL-MOCK] To {to} — {subject}")


def _layout(heading: str, body: str, cta_url: str, cta_label: str) -> str:
    return f"""\
<div style="background:#f4f6fb;padding:32px 16px;font-family:Segoe UI,Arial,sans-serif">
  <div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:12px;
              border:1px solid #e3e8f2;padding:32px">
    <div style="font-size:18px;font-weight:700;color:#0b1020;margin-bottom:4px">
      Capture<span style="color:#0891b2">Agent</span></div>
    <div style="font-size:11px;letter-spacing:.14em;color:#93a1c0;margin-bottom:24px">
      STREAMLINING GOVERNMENT CAPTURE</div>
    <h2 style="font-size:17px;color:#0b1020;margin:0 0 12px">{heading}</h2>
    <p style="font-size:14px;line-height:1.6;color:#3c4763;margin:0 0 24px">{body}</p>
    <a href="{cta_url}" style="display:inline-block;background:#0891b2;color:#ffffff;
       text-decoration:none;font-size:14px;font-weight:600;padding:11px 22px;
       border-radius:8px">{cta_label}</a>
    <p style="font-size:12px;color:#93a1c0;margin:24px 0 0">
      If the button doesn't work, paste this link into your browser:<br>
      <a href="{cta_url}" style="color:#0891b2;word-break:break-all">{cta_url}</a></p>
  </div>
  <p style="max-width:520px;margin:16px auto 0;font-size:11px;color:#93a1c0;text-align:center">
    CaptureAgent · captureagent.us · You received this because of activity on your account.</p>
</div>"""


async def send_verify(to: str, url: str):
    await send(to, "Verify your CaptureAgent email",
               _layout("Confirm your email address",
                       "Welcome to CaptureAgent. Click below to verify this email "
                       "address and activate your account. The link expires in 48 hours.",
                       url, "Verify email"))


async def send_reset(to: str, url: str):
    await send(to, "Reset your CaptureAgent password",
               _layout("Reset your password",
                       "We received a request to reset your password. Click below to "
                       "choose a new one. The link expires in 1 hour. If you didn't "
                       "request this, you can safely ignore this email.",
                       url, "Reset password"))


async def send_invite(to: str, org_name: str, url: str):
    await send(to, f"You're invited to {org_name} on CaptureAgent",
               _layout(f"Join {org_name} on CaptureAgent",
                       f"You've been invited to collaborate in the {org_name} "
                       "workspace on CaptureAgent — the AI capture and proposal "
                       "manager for government contractors. Sign in (or create your "
                       "account with this email address) to get started.",
                       url, "Accept invitation"))
