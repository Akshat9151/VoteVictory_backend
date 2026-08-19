import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, Optional

from app.adapters.base import NotificationDeliveryResult, NotificationProvider
from app.core.config import settings

logger = logging.getLogger("app.adapters.email")


class EmailProviderAdapter(NotificationProvider):
    """
    Standard Email Provider adapter supporting SMTP (STARTTLS / SSL) for Gmail, Outlook, AWS SES, etc.
    """

    def __init__(self):
        self.provider = settings.EMAIL_PROVIDER.lower()
        self.host = settings.SMTP_HOST
        self.port = int(settings.SMTP_PORT or 587)
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.sender_email = settings.SMTP_FROM_EMAIL or self.username or "noreply@electwin.com"

    async def send_message(
        self,
        recipient_address: str,
        content: str,
        template_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> NotificationDeliveryResult:
        if self.provider != "smtp" or not self.host or not self.username or not self.password:
            logger.info(
                f"[MOCK EMAIL] To: {recipient_address} | Provider: {self.provider} | "
                f"Configured: host={'yes' if self.host else 'no'}, user={'yes' if self.username else 'no'}"
            )
            return NotificationDeliveryResult(
                success=True,
                provider_message_id=f"mock_email_{recipient_address}",
                status="SENT",
                raw_response={"recipient": recipient_address, "channel": "EMAIL", "provider": "mock"},
            )

        def send() -> None:
            message = EmailMessage()
            message["Subject"] = "ElectWin - Your Verification Code"
            message["From"] = self.sender_email
            message["To"] = recipient_address
            message.set_content(content)

            # Also add an HTML version for modern email clients
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <h2 style="color: #0284c7; margin: 0;">ElectWin</h2>
                    <p style="color: #64748b; font-size: 13px; margin-top: 4px;">Election Campaign & War Room System</p>
                </div>
                <div style="background-color: #f8fafc; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                    <p style="color: #334155; font-size: 14px; margin-bottom: 12px;">Your security verification code is:</p>
                    <div style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #0f172a; margin: 10px 0;">{content.split('is ')[-1].split('.')[0] if 'is ' in content else content}</div>
                    <p style="color: #94a3b8; font-size: 12px; margin-top: 10px;">Valid for {settings.OTP_EXPIRE_MINUTES} minutes. Do not share this code with anyone.</p>
                </div>
                <p style="color: #64748b; font-size: 12px; text-align: center; margin-top: 24px;">If you did not request this code, please ignore this email.</p>
            </div>
            """
            message.add_alternative(html_content, subtype="html")

            logger.info(f"Connecting to SMTP server {self.host}:{self.port} to send email to {recipient_address}...")
            if self.port == 465:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=20) as smtp:
                    smtp.login(self.username, self.password)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=20) as smtp:
                    smtp.starttls()
                    smtp.login(self.username, self.password)
                    smtp.send_message(message)

        try:
            await asyncio.to_thread(send)
            logger.info(f"Email successfully dispatched via SMTP to {recipient_address}")
            return NotificationDeliveryResult(
                success=True,
                provider_message_id=f"smtp_{recipient_address}",
                status="SENT",
                raw_response={"recipient": recipient_address, "channel": "EMAIL", "provider": "smtp"},
            )
        except Exception as exc:
            logger.error(f"Failed to send email via SMTP to {recipient_address}: {exc}", exc_info=True)
            return NotificationDeliveryResult(success=False, status="FAILED", error_message=str(exc))

    def verify_webhook_signature(
        self,
        raw_body: bytes,
        signature_header: str,
    ) -> bool:
        return True

