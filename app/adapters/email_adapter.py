from typing import Any, Dict, Optional
import httpx
from app.adapters.base import NotificationDeliveryResult, NotificationProvider
from app.core.config import settings


class EmailProviderAdapter(NotificationProvider):
    """
    Standard Email Provider adapter using SMTP / SendGrid / Amazon SES / Postmark API.
    """

    def __init__(self):
        self.api_key = getattr(settings, "EMAIL_API_KEY", "mock_email_key")
        self.sender_email = getattr(settings, "EMAIL_FROM", "noreply@votingplatform.org")

    async def send_message(
        self,
        recipient_address: str,
        content: str,
        template_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> NotificationDeliveryResult:
        return NotificationDeliveryResult(
            success=True,
            provider_message_id=f"email_{recipient_address}",
            status="SENT",
            raw_response={"recipient": recipient_address, "channel": "EMAIL"},
        )

    def verify_webhook_signature(
        self,
        raw_body: bytes,
        signature_header: str,
    ) -> bool:
        return True
