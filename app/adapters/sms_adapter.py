import hashlib
import hmac
import logging
import re
import uuid
from typing import Any, Dict, Optional

import httpx

from app.adapters.base import NotificationProvider, ProviderSendResult
from app.core.config import settings

logger = logging.getLogger("app.adapter.sms")


class SMSProviderAdapter(NotificationProvider):
    def __init__(self):
        self.provider = settings.SMS_PROVIDER
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_FROM_NUMBER

    async def send_message(
        self,
        recipient_address: str,
        content: str,
        template_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> ProviderSendResult:
        recipient_address = self._normalize_recipient(recipient_address)
        if self.provider == "mock":
            # Production simulated mock provider
            msg_id = f"mock_sms_{uuid.uuid4().hex[:12]}"
            logger.info(f"[MOCK SMS DISPATCH] To: {recipient_address} | Body: {content}")
            return ProviderSendResult(
                success=True,
                provider_message_id=msg_id,
                status="SENT",
                raw_response={"provider": "mock_sms", "msg_id": msg_id}
            )

        if not self.account_sid or not self.auth_token or not self.from_number:
            return ProviderSendResult(
                success=False,
                status="FAILED",
                error_message="SMS provider credentials are not configured.",
            )

        # Real Twilio API integration
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    auth=(self.account_sid, self.auth_token),
                    data={
                        "To": recipient_address,
                        "From": self.from_number,
                        "Body": content,
                    }
                )
                data = resp.json()
                if resp.status_code in [200, 201]:
                    return ProviderSendResult(
                        success=True,
                        provider_message_id=data.get("sid"),
                        status="SENT",
                        raw_response=data
                    )
                else:
                    return ProviderSendResult(
                        success=False,
                        status="FAILED",
                        error_message=data.get("message", "Twilio API error"),
                        raw_response=data
                    )
        except Exception as e:
            logger.error(f"SMS Dispatch Exception: {str(e)}")
            return ProviderSendResult(
                success=False,
                status="FAILED",
                error_message=str(e)
            )

    @staticmethod
    def _normalize_recipient(recipient_address: str) -> str:
        value = re.sub(r"[\s()-]", "", (recipient_address or "").strip())
        if re.fullmatch(r"[6-9]\d{9}", value):
            return f"+91{value}"
        if value.startswith("0091") and len(value) == 14:
            return f"+{value[2:]}"
        return value

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        if not settings.WEBHOOK_SECRET_SMS:
            return True
        expected = hmac.new(settings.WEBHOOK_SECRET_SMS.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header)
