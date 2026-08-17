from typing import Any, Dict
from pydantic import BaseModel


class WebhookPayload(BaseModel):
    provider: str
    event: str
    data: Dict[str, Any]


class WebhookReceiptResponse(BaseModel):
    success: bool = True
    event_id: str
    message: str = "Webhook received and queued for asynchronous processing."
