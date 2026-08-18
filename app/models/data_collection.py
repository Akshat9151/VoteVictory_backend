import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class SubmissionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"


class DuplicateSignal(str, enum.Enum):
    MOBILE = "MOBILE"
    EMAIL = "EMAIL"
    VOTER_ID = "VOTER_ID"
    NAME_AREA = "NAME_AREA"
    COMPOSITE = "COMPOSITE"


class DuplicateResolutionStatus(str, enum.Enum):
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
    MERGED = "MERGED"
    KEPT_SEPARATE = "KEPT_SEPARATE"
    REJECTED = "REJECTED"


class ReviewAction(str, enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MERGE = "MERGE"
    FLAG_DUPLICATE = "FLAG_DUPLICATE"
    EDIT = "EDIT"


class DataSubmission(BaseModel):
    __tablename__ = "data_submissions"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    election_id = Column(String(36), ForeignKey("elections.id", ondelete="SET NULL"), nullable=True, index=True)
    volunteer_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Hierarchy mappings
    constituency_id = Column(String(36), ForeignKey("constituencies.id", ondelete="SET NULL"), nullable=True, index=True)
    ward_id = Column(String(36), nullable=True, index=True)
    booth_id = Column(String(36), nullable=True, index=True)
    area_id = Column(String(36), nullable=True, index=True)
    voter_id = Column(String(36), ForeignKey("voters.id", ondelete="SET NULL"), nullable=True, index=True)

    # Citizen/Voter Information
    citizen_name = Column(String(255), nullable=False, index=True)
    mobile = Column(String(50), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    voter_card_number = Column(String(50), nullable=True, index=True)
    date_of_birth = Column(DateTime(timezone=True), nullable=True)
    gender = Column(String(20), nullable=True)
    address_line = Column(Text, nullable=True)
    ward_no = Column(String(50), nullable=True)
    booth_no = Column(String(50), nullable=True)
    preferred_party_candidate = Column(String(255), nullable=True)
    issues_concerns = Column(Text, nullable=True)
    custom_fields_json = Column(Text, nullable=True)

    # Workflow & Quality
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.SUBMITTED, nullable=False, index=True)
    quality_score = Column(Float, default=100.0, nullable=False)
    is_flagged_duplicate = Column(Boolean, default=False, nullable=False, index=True)
    submission_channel = Column(String(50), default="MOBILE_APP", nullable=False)

    # Review metadata
    reviewed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_remarks = Column(Text, nullable=True)
    rejection_reason = Column(String(255), nullable=True)

    # Relationships
    organization = relationship("Organization")
    election = relationship("Election")
    volunteer = relationship("User", foreign_keys=[volunteer_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    voter = relationship("Voter")
    constituency = relationship("Constituency")
    quality_check = relationship("DataQualityCheck", back_populates="submission", uselist=False, cascade="all, delete-orphan")
    reviews = relationship("DataReview", back_populates="submission", cascade="all, delete-orphan")


class DataQualityCheck(BaseModel):
    __tablename__ = "data_quality_checks"

    submission_id = Column(String(36), ForeignKey("data_submissions.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    is_valid_mobile = Column(Boolean, default=True, nullable=False)
    is_valid_email = Column(Boolean, default=True, nullable=False)
    is_valid_voter_card = Column(Boolean, default=True, nullable=False)
    has_required_fields = Column(Boolean, default=True, nullable=False)
    is_area_booth_mismatch = Column(Boolean, default=False, nullable=False)
    is_suspicious_repeated = Column(Boolean, default=False, nullable=False)
    
    quality_percentage = Column(Float, default=100.0, nullable=False)
    validation_issues_json = Column(Text, nullable=True) # list of error strings

    submission = relationship("DataSubmission", back_populates="quality_check")


class DataDuplicate(BaseModel):
    __tablename__ = "data_duplicates"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    record_a_id = Column(String(36), ForeignKey("data_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    record_b_id = Column(String(36), ForeignKey("data_submissions.id", ondelete="CASCADE"), nullable=False, index=True)

    match_signal = Column(Enum(DuplicateSignal), nullable=False, index=True)
    similarity_score = Column(Float, default=1.0, nullable=False)
    match_reason = Column(String(500), nullable=False)
    
    resolution_status = Column(Enum(DuplicateResolutionStatus), default=DuplicateResolutionStatus.POSSIBLE_DUPLICATE, nullable=False, index=True)
    resolved_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    record_a = relationship("DataSubmission", foreign_keys=[record_a_id])
    record_b = relationship("DataSubmission", foreign_keys=[record_b_id])
    resolver = relationship("User", foreign_keys=[resolved_by])


class DataReview(BaseModel):
    __tablename__ = "data_reviews"

    submission_id = Column(String(36), ForeignKey("data_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    action = Column(Enum(ReviewAction), nullable=False)
    previous_status = Column(Enum(SubmissionStatus), nullable=False)
    new_status = Column(Enum(SubmissionStatus), nullable=False)
    remarks = Column(Text, nullable=True)
    reason = Column(String(255), nullable=True)

    submission = relationship("DataSubmission", back_populates="reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
