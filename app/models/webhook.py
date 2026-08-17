from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from app.models.base import BaseModel


class WebhookEvent(BaseModel):
    __tablename__ = "webhook_events"

    provider = Column(String(50), nullable=False, index=True) # SMS, WHATSAPP, INSTAGRAM
    event_type = Column(String(100), nullable=False, index=True)
    payload_json = Column(Text, nullable=False)
    signature_header = Column(String(512), nullable=True)
    signature_verified = Column(Boolean, default=False, nullable=False)
    is_processed = Column(Boolean, default=False, nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)


class SystemSetting(BaseModel):
    __tablename__ = "system_settings"

    key = Column(String(100), unique=True, nullable=False, index=True)
    value_json = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=False, nullable=False)


class FileAsset(BaseModel):
    __tablename__ = "file_assets"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    uploaded_by = Column(String(36), nullable=True)
