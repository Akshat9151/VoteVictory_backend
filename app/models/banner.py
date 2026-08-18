import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class BannerStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class Banner(BaseModel):
    __tablename__ = "banners"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    election_id = Column(String(36), ForeignKey("elections.id", ondelete="SET NULL"), nullable=True, index=True)
    campaign_id = Column(String(36), ForeignKey("notification_campaigns.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(512), nullable=False)
    cta_text = Column(String(100), nullable=True)
    cta_link = Column(String(512), nullable=True)

    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    status = Column(Enum(BannerStatus), default=BannerStatus.DRAFT, nullable=False, index=True)

    organization = relationship("Organization")
    election = relationship("Election")
    campaign = relationship("NotificationCampaign")
