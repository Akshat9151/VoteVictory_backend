import enum

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class VoterStatus(str, enum.Enum):
    REGISTERED = "REGISTERED"
    VERIFIED = "VERIFIED"
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    CHECKED_IN = "CHECKED_IN"
    VOTED = "VOTED"
    BLOCKED = "BLOCKED"
    SUSPENDED = "SUSPENDED"


class VotingStatus(str, enum.Enum):
    NOT_VOTED = "NOT_VOTED"
    CHECKED_IN = "CHECKED_IN"
    VOTED = "VOTED"


class Voter(BaseModel):
    __tablename__ = "voters"

    organization_id = Column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    election_id = Column(String(64), ForeignKey("elections.id", ondelete="CASCADE"), nullable=True, index=True)
    constituency_id = Column(String(64), ForeignKey("constituencies.id", ondelete="SET NULL"), nullable=True, index=True)
    polling_station_id = Column(String(64), ForeignKey("polling_stations.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(255), nullable=True, index=True)
    voter_id_number = Column(String(100), nullable=True, index=True) # Official EPIC / Voter ID
    first_name = Column(String(100), nullable=True, index=True)
    last_name = Column(String(100), nullable=True, index=True)
    father_or_spouse_name = Column(String(100), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(50), nullable=True)

    mobile = Column(String(50), nullable=True, index=True)
    phone_number = Column(String(50), nullable=True, index=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    house_number = Column(String(100), nullable=True)
    ward = Column(String(100), nullable=True)
    ward_name = Column(String(100), nullable=True)

    channel = Column(String(50), default="WhatsApp", nullable=True)
    consent = Column(String(50), default="Verified", nullable=True)
    source = Column(String(100), default="Official Roll", nullable=True)
    status = Column(String(50), default="Valid", nullable=True, index=True)
    voting_status = Column(Enum(VotingStatus), default=VotingStatus.NOT_VOTED, nullable=True, index=True)
    has_voted = Column(Boolean, default=False, nullable=False, index=True)
    voted_at = Column(DateTime(timezone=True), nullable=True)

    is_opt_out_notifications = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="voters")
    election = relationship("Election", back_populates="voters")
    constituency = relationship("Constituency", back_populates="voters")
    polling_station = relationship("PollingStation", back_populates="voters")
    verifications = relationship("VoterVerification", back_populates="voter", cascade="all, delete-orphan")
    checkin = relationship("VoterCheckin", back_populates="voter", uselist=False, cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class VoterVerification(BaseModel):
    __tablename__ = "voter_verifications"

    voter_id = Column(String(36), ForeignKey("voters.id", ondelete="CASCADE"), nullable=False, index=True)
    verification_method = Column(String(50), nullable=False) # OTP, ID_CARD, BIOMETRIC, MANUAL
    otp_hash = Column(String(128), nullable=True)
    otp_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_by_user_id = Column(String(36), nullable=True)
    id_document_type = Column(String(100), nullable=True)
    id_document_number = Column(String(100), nullable=True)

    voter = relationship("Voter", back_populates="verifications")


class VoterCheckin(BaseModel):
    __tablename__ = "voter_checkins"
    __table_args__ = (
        UniqueConstraint("election_id", "voter_id", name="uq_election_voter_checkin"),
    )

    voter_id = Column(String(36), ForeignKey("voters.id", ondelete="CASCADE"), nullable=False, index=True)
    election_id = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), nullable=False, index=True)
    polling_station_id = Column(String(36), ForeignKey("polling_stations.id", ondelete="CASCADE"), nullable=False, index=True)
    checked_in_by = Column(String(36), nullable=False) # User ID of volunteer/admin
    checkin_method = Column(String(50), default="VOLUNTEER_SCAN", nullable=False) # VOLUNTEER_SCAN, STATION_APP, ONLINE
    checkin_time = Column(DateTime(timezone=True), nullable=False)
    ip_address = Column(String(50), nullable=True)

    voter = relationship("Voter", back_populates="checkin")
    polling_station = relationship("PollingStation", back_populates="voter_checkins")
