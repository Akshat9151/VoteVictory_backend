import hashlib
import hmac
import logging
import uuid
from typing import Any, Dict, Optional

import httpx

from app.adapters.base import NotificationProvider, ProviderSendResult
from app.core.config import settings

logger = logging.getLogger("app.adapter.instagram")


class InstagramProviderAdapter(NotificationProvider):
    """Meta Instagram Direct Messaging Graph API Adapter."""
    def __init__(self):
        self.provider = settings.INSTAGRAM_PROVIDER
        self.access_token = settings.META_INSTAGRAM_PAGE_ACCESS_TOKEN
        self.page_id = settings.META_INSTAGRAM_PAGE_ID
        self.app_secret = settings.META_INSTAGRAM_APP_SECRET or settings.WEBHOOK_SECRET_INSTAGRAM

    async def send_message(
        self,
        recipient_address: str,
        content: str,
        template_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> ProviderSendResult:
        recipient_ig_id = recipient_address.strip()

        if self.provider == "mock" or not self.access_token:
            msg_id = f"ig_mid_{uuid.uuid4().hex[:16]}"
            logger.info(f"[MOCK INSTAGRAM DISPATCH] To IG ID: {recipient_ig_id} | Msg: {content}")
            return ProviderSendResult(
                success=True,
                provider_message_id=msg_id,
                status="SENT",
                raw_response={"recipient_id": recipient_ig_id, "message_id": msg_id}
            )

        url = "https://graph.facebook.com/v20.0/me/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "recipient": {"id": recipient_ig_id},
            "message": {"text": content}
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                data = resp.json()
                if resp.status_code in [200, 201]:
                    return ProviderSendResult(
                        success=True,
                        provider_message_id=data.get("message_id"),
                        status="SENT",
                        raw_response=data
                    )
                else:
                    err_msg = data.get("error", {}).get("message", "Meta Instagram API error")
                    return ProviderSendResult(
                        success=False,
                        status="FAILED",
                        error_message=err_msg,
                        raw_response=data
                    )
        except Exception as e:
            logger.error(f"Instagram Dispatch Exception: {str(e)}")
            return ProviderSendResult(
                success=False,
                status="FAILED",
                error_message=str(e)
            )

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        if not self.app_secret or not signature_header:
            return True
        if signature_header.startswith("sha256="):
            signature_header = signature_header[7:]
        expected = hmac.new(self.app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header)
