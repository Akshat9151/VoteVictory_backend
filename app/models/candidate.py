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

    organization_id = Column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    election_id = Column(String(64), ForeignKey("elections.id", ondelete="CASCADE"), nullable=True, index=True)
    position_id = Column(String(64), ForeignKey("positions.id", ondelete="CASCADE"), nullable=True, index=True)
    constituency_id = Column(String(64), ForeignKey("constituencies.id", ondelete="SET NULL"), nullable=True, index=True)
    
    name = Column(String(255), nullable=True, index=True)
    hindiName = Column(String(255), nullable=True)
    post = Column(String(100), nullable=True)
    postType = Column(String(50), nullable=True)
    constituency_name = Column(String(255), nullable=True)
    symbol = Column(String(50), nullable=True)
    symbolName = Column(String(100), nullable=True)
    photo = Column(String(512), nullable=True)
    slogan = Column(Text, nullable=True)
    votersCount = Column(Integer, default=0, nullable=True)
    volunteersCount = Column(Integer, default=0, nullable=True)
    manifesto = Column(Text, nullable=True)

    full_name = Column(String(255), nullable=True, index=True)
    candidate_id_number = Column(String(100), nullable=True, index=True)
    party_name = Column(String(255), nullable=True)
    party_symbol_url = Column(String(512), nullable=True)
    photo_url = Column(String(512), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    
    status = Column(Enum(CandidateStatus), default=CandidateStatus.APPROVED, nullable=False, index=True)
    display_order = Column(Integer, default=0, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    approved_by = Column(String(36), nullable=True)

    # Relationships
    organization = relationship("Organization")
    election = relationship("Election", back_populates="candidates")
    position = relationship("Position", back_populates="candidates")
    constituency = relationship("Constituency", back_populates="candidates")
    documents = relationship("CandidateDocument", back_populates="candidate", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="candidate", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        if "constituency" in kwargs and isinstance(kwargs["constituency"], str):
            kwargs["constituency_name"] = kwargs.pop("constituency")
        super().__init__(**kwargs)


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
