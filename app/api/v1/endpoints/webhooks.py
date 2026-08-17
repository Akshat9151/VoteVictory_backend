import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.adapters.instagram_adapter import InstagramProviderAdapter
from app.adapters.sms_adapter import SMSProviderAdapter
from app.adapters.whatsapp_adapter import WhatsAppProviderAdapter
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import WebhookVerificationException
from app.models.notification import DeliveryStatus, NotificationDelivery, NotificationRecipient
from app.models.webhook import WebhookEvent
from app.repositories.notification_repo import NotificationRepository
from app.schemas.common import APIResponse
from app.schemas.webhook import WebhookReceiptResponse

router = APIRouter(prefix="/webhooks", tags=["Provider Webhooks"])


@router.post("/sms", response_model=APIResponse[WebhookReceiptResponse])
async def handle_sms_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_twilio_signature: str = Header(None, alias="X-Twilio-Signature")
):
    body = await request.body()
    adapter = SMSProviderAdapter()
    if not adapter.verify_webhook_signature(body, x_twilio_signature or ""):
        raise WebhookVerificationException("SMS", "Twilio HMAC-SHA256 signature mismatch.")

    payload = await request.form() if "form" in request.headers.get("content-type", "") else await request.json()
    
    event = WebhookEvent(
        provider="SMS",
        event_type="SMS_DELIVERY_STATUS",
        payload_json=json.dumps(dict(payload)),
        signature_header=x_twilio_signature,
        signature_verified=True,
        is_processed=True,
        processed_at=datetime.now(timezone.utc)
    )
    db.add(event)
    await db.flush()

    return APIResponse(data=WebhookReceiptResponse(event_id=event.id))


@router.get("/whatsapp")
async def verify_meta_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """Meta WhatsApp Webhook subscription verification endpoint."""
    if hub_mode == "subscribe" and hub_verify_token == settings.META_WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch.")


@router.post("/whatsapp", response_model=APIResponse[WebhookReceiptResponse])
async def handle_whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256")
):
    body = await request.body()
    adapter = WhatsAppProviderAdapter()
    if not adapter.verify_webhook_signature(body, x_hub_signature_256 or ""):
        raise WebhookVerificationException("WHATSAPP", "Meta X-Hub-Signature-256 mismatch.")

    try:
        payload = json.loads(body.decode())
    except Exception:
        payload = {}

    event = WebhookEvent(
        provider="WHATSAPP",
        event_type="META_WHATSAPP_EVENT",
        payload_json=json.dumps(payload),
        signature_header=x_hub_signature_256,
        signature_verified=True,
        is_processed=True,
        processed_at=datetime.now(timezone.utc)
    )
    db.add(event)
    await db.flush()

    return APIResponse(data=WebhookReceiptResponse(event_id=event.id))


@router.post("/instagram", response_model=APIResponse[WebhookReceiptResponse])
async def handle_instagram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256")
):
    body = await request.body()
    adapter = InstagramProviderAdapter()
    if not adapter.verify_webhook_signature(body, x_hub_signature_256 or ""):
        raise WebhookVerificationException("INSTAGRAM", "Meta X-Hub-Signature-256 mismatch.")

    try:
        payload = json.loads(body.decode())
    except Exception:
        payload = {}

    event = WebhookEvent(
        provider="INSTAGRAM",
        event_type="META_INSTAGRAM_EVENT",
        payload_json=json.dumps(payload),
        signature_header=x_hub_signature_256,
        signature_verified=True,
        is_processed=True,
        processed_at=datetime.now(timezone.utc)
    )
    db.add(event)
    await db.flush()

    return APIResponse(data=WebhookReceiptResponse(event_id=event.id))
