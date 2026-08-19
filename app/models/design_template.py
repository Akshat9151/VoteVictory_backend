import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text
from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class DesignTemplate(Base):
    """
    Campaign Creative Design Template (Section 7.6).
    Stores poster, banner, and ID card layouts with element JSON for Design Studio.
    """
    __tablename__ = "design_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    election_type = Column(String(100), nullable=True, default="panchayat")
    category = Column(String(100), nullable=False, default="poster")  # poster, banner, id_card, social
    format_name = Column(String(100), nullable=True)  # A4 Poster, Hoarding Banner, ID Card, etc.
    format_dims = Column(String(100), nullable=True)  # 210 × 297 mm, 1200 × 600 px, etc.
    layout_json = Column(JSON, nullable=False, default=dict)
    thumbnail_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=1, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
