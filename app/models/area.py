import enum

from sqlalchemy import Column, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class MapStatus(str, enum.Enum):
    GREEN = "GREEN"   # target achieved (>= 100%)
    YELLOW = "YELLOW" # in progress (50% - 99%)
    RED = "RED"       # low collection (< 50%)
    GREY = "GREY"     # no activity (0%)


class BoothStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    CLOSED = "CLOSED"


class Ward(BaseModel):
    __tablename__ = "wards"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    constituency_id = Column(String(36), ForeignKey("constituencies.id", ondelete="CASCADE"), nullable=True, index=True)

    ward_number = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    constituency = relationship("Constituency")
    booths = relationship("Booth", back_populates="ward", cascade="all, delete-orphan")


class Booth(BaseModel):
    __tablename__ = "booths"
    __table_args__ = {"extend_existing": True}

    organization_id = Column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    constituency_id = Column(String(64), ForeignKey("constituencies.id", ondelete="CASCADE"), nullable=True, index=True)
    ward_id = Column(String(64), ForeignKey("wards.id", ondelete="SET NULL"), nullable=True, index=True)

    booth_number = Column(String(50), nullable=False, index=True, default="Booth 01")
    boothNo = Column(String(50), nullable=True, index=True)
    name = Column(String(255), nullable=True, default="Booth")
    location = Column(String(255), nullable=True)
    location_address = Column(Text, nullable=True)
    incharge = Column(String(150), nullable=True, default="Booth Incharge")
    voters = Column(Integer, default=0, nullable=False)
    slips = Column(Integer, default=0, nullable=False)
    coverage = Column(String(32), default="0%", nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    target = Column(Integer, default=1000, nullable=False)
    collected_count = Column(Integer, default=0, nullable=False)
    status = Column(Enum(BoothStatus), default=BoothStatus.ACTIVE, nullable=False, index=True)

    ward = relationship("Ward", back_populates="booths")
    constituency = relationship("Constituency")
    areas = relationship("Area", back_populates="booth", cascade="all, delete-orphan")


class Area(BaseModel):
    __tablename__ = "areas"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    constituency_id = Column(String(36), ForeignKey("constituencies.id", ondelete="CASCADE"), nullable=True, index=True)
    ward_id = Column(String(36), ForeignKey("wards.id", ondelete="SET NULL"), nullable=True, index=True)
    booth_id = Column(String(36), ForeignKey("booths.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    area_type = Column(String(50), default="SECTOR", nullable=False)
    description = Column(Text, nullable=True)
    boundary_coordinates = Column(Text, nullable=True)
    center_latitude = Column(Float, nullable=True)
    center_longitude = Column(Float, nullable=True)

    target_count = Column(Integer, default=500, nullable=False)
    collected_count = Column(Integer, default=0, nullable=False)
    verified_count = Column(Integer, default=0, nullable=False)

    ward = relationship("Ward")
    booth = relationship("Booth", back_populates="areas")
    constituency = relationship("Constituency")
