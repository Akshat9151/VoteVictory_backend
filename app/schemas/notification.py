from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.notification import CampaignStatus, DeliveryStatus, NotificationChannel


class TemplateBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=100)
    channel: NotificationChannel = NotificationChannel.WHATSAPP
    template_type: str = "TRANSACTIONAL"
    external_template_id: Optional[str] = None
    content_template: str = Field(..., min_length=5)
    variables_schema_json: Optional[str] = None


class TemplateCreate(TemplateBase):
    organization_id: Optional[str] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    content_template: Optional[str] = None
    external_template_id: Optional[str] = None
    is_approved: Optional[bool] = None


class TemplateResponse(TemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: Optional[str] = None
    is_approved: bool
    created_at: datetime


class TemplateVariablePreviewRequest(BaseModel):
    template_id: str
    sample_data: Dict[str, str] = Field(
        default_factory=lambda: {
            "name": "Alex Johnson",
            "election_name": "General Election 2026",
            "area": "Downtown Sector 4",
            "booth": "Booth 12A",
            "date": "2026-11-04",
            "time": "08:00 AM - 05:00 PM",
            "polling_station": "City Central High School",
        }
    )


class TemplateVariablePreviewResponse(BaseModel):
    template_id: str
    original_template: str
    rendered_preview: str
    missing_variables: List[str] = []
    is_valid: bool = True


class SendMessageRequest(BaseModel):
    channel: NotificationChannel
    recipient_address: str = Field(..., description="Phone number or Instagram handle")
    recipient_name: Optional[str] = None
    template_id: Optional[str] = None
    message_text: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    election_id: Optional[str] = None
    template_id: str
    channel: NotificationChannel = NotificationChannel.WHATSAPP
    target_audience_type: str = "ALL_VOTERS" # ALL_VOTERS, ELIGIBLE, NOT_VOTED, CONSTITUENCY, POLLING_STATION, AREA, BOOTH
    audience_filter: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    election_id: Optional[str] = None
    template_id: str
    name: str
    channel: NotificationChannel
    target_audience_type: str
    status: CampaignStatus
    total_recipients: int
    sent_count: int
    delivered_count: int
    failed_count: int
    scheduled_at: Optional[datetime] = None
    created_at: datetime


class DeliveryReportItem(BaseModel):
    recipient_name: Optional[str] = None
    recipient_address: str
    channel: str
    status: DeliveryStatus
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None


class DeliveryReportResponse(BaseModel):
    campaign_id: str
    total_recipients: int
    sent_count: int
    delivered_count: int
    failed_count: int
    deliveries: List[DeliveryReportItem] = []
