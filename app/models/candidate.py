import enum
from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class CandidateStatus(str, enum.Enum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class Candidate(BaseModel):
    __tablename__ = "candidates"

    election_id = Column(String(36), ForeignKey("elections.id", ondelete="CASCADE"), nullable=False, index=True)
    position_id = Column(String(36), ForeignKey("positions.id", ondelete="CASCADE"), nullable=False, index=True)
    constituency_id = Column(String(36), ForeignKey("constituencies.id", ondelete="SET NULL"), nullable=True, index=True)
    
    full_name = Column(String(255), nullable=False, index=True)
    candidate_id_number = Column(String(100), nullable=True, index=True)
    party_name = Column(String(255), nullable=True)
    party_symbol_url = Column(String(512), nullable=True)
    photo_url = Column(String(512), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    manifesto = Column(Text, nullable=True)
    
    status = Column(Enum(CandidateStatus), default=CandidateStatus.PENDING, nullable=False, index=True)
    display_order = Column(Integer, default=0, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    approved_by = Column(String(36), nullable=True)

    # Relationships
    election = relationship("Election", back_populates="candidates")
    position = relationship("Position", back_populates="candidates")
    constituency = relationship("Constituency", back_populates="candidates")
    documents = relationship("CandidateDocument", back_populates="candidate", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="candidate", cascade="all, delete-orphan")


class CandidateDocument(BaseModel):
    __tablename__ = "candidate_documents"

    candidate_id = Column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(String(100), nullable=False) # e.g. AFFIDAVIT, NOMINATION_FORM, ID_PROOF
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    verification_status = Column(String(50), default="PENDING", nullable=False) # PENDING, VERIFIED, REJECTED
    notes = Column(Text, nullable=True)

    candidate = relationship("Candidate", back_populates="documents")
