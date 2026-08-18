import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class NotificationChannel(str, enum.Enum):
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    INSTAGRAM = "INSTAGRAM"
    EMAIL = "EMAIL"


class CampaignStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


class NotificationTemplate(BaseModel):
    __tablename__ = "notification_templates"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), nullable=False, index=True) # e.g. 'VOTING_REMINDER', 'OTP_VERIFICATION'
    channel = Column(Enum(NotificationChannel), default=NotificationChannel.WHATSAPP, nullable=False)
    template_type = Column(String(50), default="TRANSACTIONAL", nullable=False)
    external_template_id = Column(String(255), nullable=True) # Provider approved template ID (Meta / DLT)
    content_template = Column(Text, nullable=False)
    variables_schema_json = Column(Text, nullable=True) # JSON list of required variables e.g. ["name", "polling_station"]
    is_approved = Column(Boolean, default=True, nullable=False)

    campaigns = relationship("NotificationCampaign", back_populates="template")


class NotificationCampaign(BaseModel):
    __tablename__ = "notification_campaigns"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    election_id = Column(String(36), ForeignKey("elections.id", ondelete="SET NULL"), nullable=True, index=True)
    template_id = Column(String(36), ForeignKey("notification_templates.id", ondelete="RESTRICT"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    channel = Column(Enum(NotificationChannel), default=NotificationChannel.WHATSAPP, nullable=False)
    target_audience_type = Column(String(50), default="ALL_VOTERS", nullable=False) # ALL_VOTERS, ELIGIBLE, NOT_VOTED, CONSTITUENCY, POLLING_STATION, CUSTOM
    audience_filter_json = Column(Text, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False, index=True)

    total_recipients = Column(Integer, default=0, nullable=False)
    sent_count = Column(Integer, default=0, nullable=False)
    delivered_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    created_by = Column(String(36), nullable=True)

    organization = relationship("Organization", back_populates="notification_campaigns")
    template = relationship("NotificationTemplate", back_populates="campaigns")
    recipients = relationship("NotificationRecipient", back_populates="campaign", cascade="all, delete-orphan")


class NotificationRecipient(BaseModel):
    __tablename__ = "notification_recipients"

    campaign_id = Column(String(36), ForeignKey("notification_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    voter_id = Column(String(36), ForeignKey("voters.id", ondelete="SET NULL"), nullable=True, index=True)

    recipient_address = Column(String(255), nullable=False, index=True) # Phone number or IG handle
    recipient_name = Column(String(255), nullable=True)
    personalized_data_json = Column(Text, nullable=True)
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.PENDING, nullable=False, index=True)

    provider_message_id = Column(String(255), nullable=True, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    campaign = relationship("NotificationCampaign", back_populates="recipients")
    deliveries = relationship("NotificationDelivery", back_populates="recipient", cascade="all, delete-orphan")


class NotificationDelivery(BaseModel):
    __tablename__ = "notification_deliveries"

    recipient_id = Column(String(36), ForeignKey("notification_recipients.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_name = Column(String(100), nullable=False) # e.g. TWILIO, META_WHATSAPP, META_INSTAGRAM
    event_type = Column(String(50), nullable=False) # SENT, DELIVERED, READ, FAILED
    provider_response_json = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)

    recipient = relationship("NotificationRecipient", back_populates="deliveries")
