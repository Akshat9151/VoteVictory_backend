import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ResultStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    COUNTING = "COUNTING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"


class Result(BaseModel):
    __tablename__ = "results"

    election_id = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), nullable=False, index=True)
    position_id = Column(String(36), ForeignKey("positions.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    polling_station_id = Column(String(36), ForeignKey("polling_stations.id", ondelete="SET NULL"), nullable=True, index=True)
    
    vote_count = Column(Integer, default=0, nullable=False)
    vote_percentage = Column(Float, default=0.0, nullable=False)
    rank = Column(Integer, default=0, nullable=False)
    status = Column(Enum(ResultStatus), default=ResultStatus.NOT_STARTED, nullable=False)
    
    counted_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String(36), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    election = relationship("Election", back_populates="results")
    position = relationship("Position", back_populates="results")
    candidate = relationship("Candidate", back_populates="results")


class ResultSummary(BaseModel):
    __tablename__ = "result_summaries"

    election_id = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_eligible_voters = Column(Integer, default=0, nullable=False)
    total_checked_in = Column(Integer, default=0, nullable=False)
    total_votes_cast = Column(Integer, default=0, nullable=False)
    total_invalid_ballots = Column(Integer, default=0, nullable=False)
    turnout_percentage = Column(Float, default=0.0, nullable=False)
    
    status = Column(Enum(ResultStatus), default=ResultStatus.NOT_STARTED, nullable=False)
    approved_by = Column(String(36), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    election = relationship("Election", back_populates="result_summary")
