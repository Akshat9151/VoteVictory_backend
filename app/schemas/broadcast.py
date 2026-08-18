from typing import List, Optional
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
