import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class ElectionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    UPCOMING = "UPCOMING"
    LIVE = "LIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"
    COUNTING = "COUNTING"
    RESULT_PUBLISHED = "RESULT_PUBLISHED"
    ARCHIVED = "ARCHIVED"
    CANCELLED = "CANCELLED"


class ElectionType(str, enum.Enum):
    GENERAL = "GENERAL"
    LOCAL = "LOCAL"
    WARD = "WARD"
    STUDENT = "STUDENT"
    CORPORATE = "CORPORATE"
    PRIMARY = "PRIMARY"


class ElectionVisibility(str, enum.Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class Election(BaseModel):
    __tablename__ = "elections"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    election_type = Column(Enum(ElectionType), default=ElectionType.LOCAL, nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    start_datetime = Column(DateTime(timezone=True), nullable=True)
    end_datetime = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(ElectionStatus), default=ElectionStatus.DRAFT, nullable=False, index=True)
    visibility = Column(Enum(ElectionVisibility), default=ElectionVisibility.PRIVATE, nullable=False)
    created_by = Column(String(36), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="elections")
    settings = relationship("ElectionSetting", back_populates="election", uselist=False, cascade="all, delete-orphan")
    constituencies = relationship("Constituency", back_populates="election", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="election", cascade="all, delete-orphan")
    candidates = relationship("Candidate", back_populates="election", cascade="all, delete-orphan")
    voters = relationship("Voter", back_populates="election", cascade="all, delete-orphan")
    polling_stations = relationship("PollingStation", back_populates="election", cascade="all, delete-orphan")
    volunteer_assignments = relationship("VolunteerAssignment", back_populates="election", cascade="all, delete-orphan")
    ballots = relationship("Ballot", back_populates="election", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="election", cascade="all, delete-orphan")
    result_summary = relationship("ResultSummary", back_populates="election", uselist=False, cascade="all, delete-orphan")


class ElectionSetting(BaseModel):
    __tablename__ = "election_settings"

    election_id = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), unique=True, nullable=False)
    allow_electronic_voting = Column(Boolean, default=True, nullable=False)
    require_voter_mfa = Column(Boolean, default=False, nullable=False)
    require_photo_id = Column(Boolean, default=False, nullable=False)
    allow_abstain = Column(Boolean, default=True, nullable=False)
    result_publication_policy = Column(String(50), default="MANUAL_APPROVAL", nullable=False)
    notification_rules_json = Column(Text, nullable=True) # Automated reminders configuration

    election = relationship("Election", back_populates="settings")


class Constituency(BaseModel):
    __tablename__ = "constituencies"

    election_id = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True, index=True)
    description = Column(Text, nullable=True)

    election = relationship("Election", back_populates="constituencies")
    positions = relationship("Position", back_populates="constituency")
    candidates = relationship("Candidate", back_populates="constituency")
    polling_stations = relationship("PollingStation", back_populates="constituency")
    voters = relationship("Voter", back_populates="constituency")


class Position(BaseModel):
    __tablename__ = "positions"

    election_id = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), nullable=False, index=True)
    constituency_id = Column(String(36), ForeignKey("constituencies.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    min_selections = Column(Integer, default=1, nullable=False)
    max_selections = Column(Integer, default=1, nullable=False)
    candidate_limit = Column(Integer, default=50, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    election = relationship("Election", back_populates="positions")
    constituency = relationship("Constituency", back_populates="positions")
    candidates = relationship("Candidate", back_populates="position", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="position", cascade="all, delete-orphan")
