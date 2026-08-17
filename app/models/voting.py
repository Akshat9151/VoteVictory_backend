import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class VotingSessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    USED = "USED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class VotingSession(BaseModel):
    __tablename__ = "voting_sessions"

    election_id = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), nullable=False, index=True)
    voter_token_hash = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(Enum(VotingSessionStatus), default=VotingSessionStatus.ACTIVE, nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    client_ip = Column(String(50), nullable=True)


class Ballot(BaseModel):
    """
    Anonymous Ballot Vault.
    Strictly isolated from voter personal identification to guarantee constitutionally compliant ballot secrecy.
    """
    __tablename__ = "ballots"

    election_id = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), nullable=False, index=True)
    constituency_id = Column(String(36), ForeignKey("constituencies.id", ondelete="SET NULL"), nullable=True, index=True)
    ballot_serial_hash = Column(String(64), unique=True, nullable=False, index=True) # Cryptographic HMAC for audit verifiability
    cast_timestamp = Column(DateTime(timezone=True), nullable=False)
    is_valid = Column(Boolean, default=True, nullable=False)

    election = relationship("Election", back_populates="ballots")
    votes = relationship("Vote", back_populates="ballot", cascade="all, delete-orphan")


class Vote(BaseModel):
    """Individual position-candidate choice for an anonymous ballot."""
    __tablename__ = "votes"

    ballot_id = Column(String(36), ForeignKey("ballots.id", ondelete="CASCADE"), nullable=False, index=True)
    position_id = Column(String(36), ForeignKey("positions.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)

    ballot = relationship("Ballot", back_populates="votes")
