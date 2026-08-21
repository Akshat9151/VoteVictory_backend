import asyncio
import json
import logging
import smtplib
import urllib.request
import urllib.error
from email.message import EmailMessage
from typing import Any, Dict, Optional

from app.adapters.base import NotificationDeliveryResult, NotificationProvider
from app.core.config import settings

logger = logging.getLogger("app.adapters.email")


class EmailProviderAdapter(NotificationProvider):
    """
    Multi-Provider Email Adapter supporting:
    1. HTTP APIs (Resend, Brevo/Sendinblue, SendGrid) — Works 100% on Render Free Tier via Port 443 (HTTPS)
    2. SMTP (STARTTLS / SSL) — For standard SMTP servers where ports 587/465 are open
    """

    def __init__(self):
        self.provider = settings.EMAIL_PROVIDER.lower()
        self.host = settings.SMTP_HOST
        self.port = int(settings.SMTP_PORT or 587)
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.sender_email = settings.SMTP_FROM_EMAIL or self.username or "onboarding@resend.dev"
        self.resend_api_key = settings.RESEND_API_KEY
        self.brevo_api_key = settings.BREVO_API_KEY
        self.sendgrid_api_key = settings.SENDGRID_API_KEY

    async def send_message(
        self,
        recipient_address: str,
        content: str,
        template_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> NotificationDeliveryResult:
        subject = "VoteVictory - Your Verification Code"
        otp_code = content.split("is ")[-1].split(".")[0] if "is " in content else content
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: #0284c7; margin: 0;">VoteVictory</h2>
                <p style="color: #64748b; font-size: 13px; margin-top: 4px;">Election Campaign Management System</p>
            </div>
            <div style="background-color: #f8fafc; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                <p style="color: #334155; font-size: 14px; margin-bottom: 12px;">Your security verification code is:</p>
                <div style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #0f172a; margin: 10px 0;">{otp_code}</div>
                <p style="color: #94a3b8; font-size: 12px; margin-top: 10px;">Valid for {settings.OTP_EXPIRE_MINUTES} minutes. Do not share this code with anyone.</p>
            </div>
            <p style="color: #64748b; font-size: 12px; text-align: center; margin-top: 24px;">If you did not request this code, please ignore this email.</p>
        </div>
        """

        # ── 1. Resend HTTP API (HTTPS Port 443 — Render Free Tier Friendly) ──
        if self.resend_api_key or self.provider == "resend":
            return await self._send_via_resend(recipient_address, subject, content, html_content)

        # ── 2. Brevo HTTP API (HTTPS Port 443 — Render Free Tier Friendly) ──
        if self.brevo_api_key or self.provider == "brevo":
            return await self._send_via_brevo(recipient_address, subject, content, html_content)

        # ── 3. SendGrid HTTP API (HTTPS Port 443) ──
        if self.sendgrid_api_key or self.provider == "sendgrid":
            return await self._send_via_sendgrid(recipient_address, subject, content, html_content)

        # ── 4. Standard SMTP (Ports 587/465) ──
        is_smtp = (self.provider == "smtp") or bool(self.host and self.username and self.password)
        if is_smtp and self.host and self.username and self.password:
            return await self._send_via_smtp(recipient_address, subject, content, html_content)

        # ── Not Configured ──
        logger.warning(f"[EMAIL NOT CONFIGURED] To: {recipient_address}")
        return NotificationDeliveryResult(
            success=False,
            status="FAILED",
            error_message="Email provider not configured. Please add RESEND_API_KEY or SMTP credentials in Render Environment variables.",
        )

    async def _send_via_resend(self, recipient: str, subject: str, text: str, html: str) -> NotificationDeliveryResult:
        def call_resend():
            # Resend requires onboarding@resend.dev unless a custom domain is verified
            is_unverified = any(d in (self.sender_email or "").lower() for d in ["@gmail.", "@yahoo.", "@outlook.", "@hotmail.", "@yopmail.", "@votingplatform.", "@electwin."])
            from_sender = "VoteVictory <onboarding@resend.dev>"
            if self.sender_email and "@" in self.sender_email and not is_unverified:
                from_sender = f"VoteVictory <{self.sender_email}>"

            payload = {
                "from": from_sender,
                "to": [recipient],
                "subject": subject,
                "text": text,
                "html": html,
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.resend_api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "VoteVictory/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return res_data.get("id", "resend_msg")

        try:
            msg_id = await asyncio.to_thread(call_resend)
            logger.info(f"Email sent via Resend HTTP API to {recipient} (ID: {msg_id})")
            return NotificationDeliveryResult(success=True, provider_message_id=msg_id, status="SENT")
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="ignore")
            logger.error(f"Resend HTTP API error for {recipient}: {err_body}")
            return NotificationDeliveryResult(success=False, status="FAILED", error_message=f"Resend API error: {err_body}")
        except Exception as exc:
            logger.error(f"Resend dispatch error: {exc}", exc_info=True)
            return NotificationDeliveryResult(success=False, status="FAILED", error_message=str(exc))

    async def _send_via_brevo(self, recipient: str, subject: str, text: str, html: str) -> NotificationDeliveryResult:
        def call_brevo():
            url = "https://api.brevo.com/v3/smtp/email"
            payload = {
                "sender": {"name": "VoteVictory", "email": self.sender_email if "@" in self.sender_email else "noreply@votevictory.com"},
                "to": [{"email": recipient}],
                "subject": subject,
                "textContent": text,
                "htmlContent": html,
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "api-key": self.brevo_api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "VoteVictory/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return res_data.get("messageId", "brevo_msg")

        try:
            msg_id = await asyncio.to_thread(call_brevo)
            logger.info(f"Email sent via Brevo HTTP API to {recipient}")
            return NotificationDeliveryResult(success=True, provider_message_id=msg_id, status="SENT")
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="ignore")
            logger.error(f"Brevo HTTP API error: {err_body}")
            return NotificationDeliveryResult(success=False, status="FAILED", error_message=f"Brevo API error: {err_body}")
        except Exception as exc:
            logger.error(f"Brevo dispatch error: {exc}", exc_info=True)
            return NotificationDeliveryResult(success=False, status="FAILED", error_message=str(exc))

    async def _send_via_sendgrid(self, recipient: str, subject: str, text: str, html: str) -> NotificationDeliveryResult:
        def call_sendgrid():
            url = "https://api.sendgrid.com/v3/mail/send"
            payload = {
                "personalizations": [{"to": [{"email": recipient}]}],
                "from": {"email": self.sender_email},
                "subject": subject,
                "content": [{"type": "text/html", "value": html}],
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.sendgrid_api_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return "sendgrid_sent"

        try:
            msg_id = await asyncio.to_thread(call_sendgrid)
            return NotificationDeliveryResult(success=True, provider_message_id=msg_id, status="SENT")
        except Exception as exc:
            logger.error(f"SendGrid error: {exc}", exc_info=True)
            return NotificationDeliveryResult(success=False, status="FAILED", error_message=str(exc))

    async def _send_via_smtp(self, recipient: str, subject: str, text: str, html: str) -> NotificationDeliveryResult:
        def send_smtp():
            message = EmailMessage()
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient
            message.set_content(text)
            message.add_alternative(html, subtype="html")

            if self.port == 465:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=20) as smtp:
                    smtp.login(self.username, self.password)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=20) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
                    smtp.login(self.username, self.password)
                    smtp.send_message(message)

        try:
            await asyncio.to_thread(send_smtp)
            logger.info(f"Email dispatched via SMTP to {recipient}")
            return NotificationDeliveryResult(success=True, provider_message_id=f"smtp_{recipient}", status="SENT")
        except Exception as exc:
            logger.error(f"SMTP dispatch error for {recipient}: {exc}", exc_info=True)
            return NotificationDeliveryResult(success=False, status="FAILED", error_message=str(exc))

    def verify_webhook_signature(
        self,
        raw_body: bytes,
        signature_header: str,
    ) -> bool:
        return True
