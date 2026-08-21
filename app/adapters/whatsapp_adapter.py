import hashlib
import hmac
import logging
import uuid
from typing import Any, Dict, Optional

import httpx

from app.adapters.base import NotificationProvider, ProviderSendResult
from app.core.config import settings

logger = logging.getLogger("app.adapter.whatsapp")


class WhatsAppProviderAdapter(NotificationProvider):
    def __init__(self):
        self.provider = settings.WHATSAPP_PROVIDER
        self.access_token = settings.META_WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.META_WHATSAPP_PHONE_NUMBER_ID
        self.twilio_account_sid = settings.TWILIO_ACCOUNT_SID
        self.twilio_auth_token = settings.TWILIO_AUTH_TOKEN
        self.twilio_from_number = settings.TWILIO_WHATSAPP_FROM_NUMBER
        self.app_secret = settings.META_WHATSAPP_APP_SECRET or settings.WEBHOOK_SECRET_WHATSAPP

    async def send_message(
        self,
        recipient_address: str,
        content: str,
        template_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> ProviderSendResult:
        clean_phone = recipient_address.replace("+", "").replace(" ", "").replace("-", "")

        if self.provider == "mock":
            msg_id = f"wamid.mock_{uuid.uuid4().hex[:16]}"
            logger.info(f"[MOCK WHATSAPP DISPATCH] To: {clean_phone} | Msg: {content}")
            return ProviderSendResult(
                success=True,
                provider_message_id=msg_id,
                status="SENT",
                raw_response={"messaging_product": "whatsapp", "messages": [{"id": msg_id}]}
            )

        if self.provider == "twilio":
            if not self.twilio_account_sid or not self.twilio_auth_token or not self.twilio_from_number:
                return ProviderSendResult(success=False, status="FAILED", error_message="Twilio WhatsApp credentials are not configured.")
            try:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        url,
                        auth=(self.twilio_account_sid, self.twilio_auth_token),
                        data={
                            "To": f"whatsapp:{clean_phone}",
                            "From": f"whatsapp:{self.twilio_from_number}",
                            "Body": content,
                        },
                    )
                    data = resp.json()
                    return ProviderSendResult(
                        success=resp.status_code in [200, 201],
                        provider_message_id=data.get("sid"),
                        status="SENT" if resp.status_code in [200, 201] else "FAILED",
                        error_message=data.get("message") if resp.status_code not in [200, 201] else None,
                        raw_response=data,
                    )
            except Exception as e:
                return ProviderSendResult(success=False, status="FAILED", error_message=str(e))

        if not self.access_token or not self.phone_number_id:
            return ProviderSendResult(success=False, status="FAILED", error_message="WhatsApp provider credentials are not configured.")

        # Meta WhatsApp Cloud API v20.0+
        url = f"https://graph.facebook.com/v20.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # Build payload: Template vs Text
        if template_id:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": clean_phone,
                "type": "template",
                "template": {
                    "name": template_id,
                    "language": {"code": "en_US"},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": str(v)}
                                for v in (variables or {}).values()
                            ]
                        }
                    ]
                }
            }
        else:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": clean_phone,
                "type": "text",
                "text": {"preview_url": False, "body": content}
            }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                data = resp.json()
                if resp.status_code in [200, 201]:
                    wamid = data.get("messages", [{}])[0].get("id")
                    return ProviderSendResult(
                        success=True,
                        provider_message_id=wamid,
                        status="SENT",
                        raw_response=data
                    )
                else:
                    err_msg = data.get("error", {}).get("message", "Meta WhatsApp API error")
                    return ProviderSendResult(
                        success=False,
                        status="FAILED",
                        error_message=err_msg,
                        raw_response=data
                    )
        except Exception as e:
            logger.error(f"WhatsApp Dispatch Exception: {str(e)}")
            return ProviderSendResult(
                success=False,
                status="FAILED",
                error_message=str(e)
            )

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """Meta Cloud API sends X-Hub-Signature-256: sha256=<hash>."""
        if not self.app_secret or not signature_header:
            return True

        if signature_header.startswith("sha256="):
            signature_header = signature_header[7:]

        expected = hmac.new(self.app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header)
