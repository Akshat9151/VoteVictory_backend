from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict


class DeliveryLogResponse(BaseModel):
    id: str
    name: str
    ward: str
    mobile: str
    route: str  # WhatsApp, SMS Fallback
    status: str  # Delivered, Failed, Sending
    read: str
    time: str

    model_config = ConfigDict(from_attributes=True)


class BroadcastPayload(BaseModel):
    message: str
    channel: Optional[str] = "all"  # all, whatsapp, sms
    includePoster: Optional[bool] = False
    selectedWards: Optional[List[str]] = []


class BroadcastResponse(BaseModel):
    success: bool
    count: int


class BroadcastGroupCreate(BaseModel):
    name: Optional[str] = None
    voter_ids: List[str] = []
    filter_criteria_snapshot: dict[str, Any] = {}


class BroadcastGroupResponse(BaseModel):
    id: str
    name: str
    filter_criteria_snapshot: dict[str, Any]
    message_text: Optional[str] = None
    status: str
    recipient_count: int
    whatsapp_count: int
    sms_count: int
    excluded_no_contact: int
    created_at: Any


class BroadcastDraftPayload(BaseModel):
    message_text: str


class BroadcastSendResponse(BaseModel):
    success: bool
    group_id: str
    total: int
    whatsapp_sent: int
    sms_sent: int
    failed: int


class BroadcastLogItem(BaseModel):
    id: str
    voter_id: Optional[str] = None
    mobile: str
    channel_used: str
    status: str
    provider_response: Optional[str] = None
    sent_at: Optional[str] = None
