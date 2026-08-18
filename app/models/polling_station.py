import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class PollingStationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    CLOSED = "CLOSED"


class PollingStation(BaseModel):
    __tablename__ = "polling_stations"

    election_id = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), nullable=False, index=True)
    constituency_id = Column(String(36), ForeignKey("constituencies.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    address = Column(Text, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    capacity = Column(Integer, default=1000, nullable=False)
    operating_hours = Column(String(100), default="08:00 - 18:00", nullable=False)
    status = Column(Enum(PollingStationStatus), default=PollingStationStatus.ACTIVE, nullable=False)

    # Relationships
    election = relationship("Election", back_populates="polling_stations")
    constituency = relationship("Constituency", back_populates="polling_stations")
    voters = relationship("Voter", back_populates="polling_station")
    volunteer_assignments = relationship("VolunteerAssignment", back_populates="polling_station", cascade="all, delete-orphan")
    voter_checkins = relationship("VoterCheckin", back_populates="polling_station")


class VolunteerAssignment(BaseModel):
    __tablename__ = "volunteer_assignments"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    election_id = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), nullable=False, index=True)
    polling_station_id = Column(String(36), ForeignKey("polling_stations.id", ondelete="CASCADE"), nullable=False, index=True)

    assigned_by = Column(String(36), nullable=True)
    shift_start = Column(DateTime(timezone=True), nullable=True)
    shift_end = Column(DateTime(timezone=True), nullable=True)
    task_role = Column(String(100), default="VERIFICATION_OFFICER", nullable=False) # e.g. VERIFICATION_OFFICER, QUEUE_MANAGER, HELP_DESK
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="volunteer_assignments")
    election = relationship("Election", back_populates="volunteer_assignments")
    polling_station = relationship("PollingStation", back_populates="volunteer_assignments")
