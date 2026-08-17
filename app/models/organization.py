import enum
from sqlalchemy import Column, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class OrganizationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"


class Organization(BaseModel):
    __tablename__ = "organizations"

    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(Enum(OrganizationStatus), default=OrganizationStatus.ACTIVE, nullable=False)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    settings_json = Column(Text, nullable=True) # JSON configuration
    created_by = Column(String(36), nullable=True)

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    elections = relationship("Election", back_populates="organization", cascade="all, delete-orphan")
    voters = relationship("Voter", back_populates="organization", cascade="all, delete-orphan")
    notification_campaigns = relationship("NotificationCampaign", back_populates="organization", cascade="all, delete-orphan")
