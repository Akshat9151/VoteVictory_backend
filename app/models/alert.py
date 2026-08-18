import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class OperationalAlertType(str, enum.Enum):
    VOLUNTEER_INACTIVE = "VOLUNTEER_INACTIVE"
    TARGET_BELOW_THRESHOLD = "TARGET_BELOW_THRESHOLD"
    HIGH_DUPLICATE_RATE = "HIGH_DUPLICATE_RATE"
    HIGH_REJECTION_RATE = "HIGH_REJECTION_RATE"
    DATA_QUALITY_DROP = "DATA_QUALITY_DROP"
    IMPORT_FAILURE = "IMPORT_FAILURE"
    CAMPAIGN_FAILURE = "CAMPAIGN_FAILURE"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    ELECTION_APPROACHING = "ELECTION_APPROACHING"
    ELECTION_LIVE = "ELECTION_LIVE"
    ELECTION_CLOSING = "ELECTION_CLOSING"
    SECURITY_EVENT = "SECURITY_EVENT"


class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OperationalAlert(BaseModel):
    __tablename__ = "operational_alerts"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    election_id = Column(String(36), ForeignKey("elections.id", ondelete="SET NULL"), nullable=True, index=True)

    alert_type = Column(Enum(OperationalAlertType), nullable=False, index=True)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.MEDIUM, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)

    is_resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    organization = relationship("Organization")
    election = relationship("Election")
    resolver = relationship("User", foreign_keys=[resolved_by])
