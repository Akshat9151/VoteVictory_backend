from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr
from app.models.data_collection import (
    SubmissionStatus,
    DuplicateSignal,
    DuplicateResolutionStatus,
    ReviewAction,
)


class DataSubmissionCreate(BaseModel):
    citizen_name: str
    mobile: Optional[str] = None
    email: Optional[EmailStr] = None
    voter_card_number: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    address_line: Optional[str] = None
    ward_no: Optional[str] = None
    booth_no: Optional[str] = None
    constituency_id: Optional[str] = None
    ward_id: Optional[str] = None
    booth_id: Optional[str] = None
    area_id: Optional[str] = None
    election_id: Optional[str] = None
    preferred_party_candidate: Optional[str] = None
    issues_concerns: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None
    submission_channel: str = "MOBILE_APP"


class DataSubmissionUpdate(BaseModel):
    citizen_name: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[EmailStr] = None
    voter_card_number: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    address_line: Optional[str] = None
    ward_no: Optional[str] = None
    booth_no: Optional[str] = None
    constituency_id: Optional[str] = None
    ward_id: Optional[str] = None
    booth_id: Optional[str] = None
    area_id: Optional[str] = None
    preferred_party_candidate: Optional[str] = None
    issues_concerns: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class DataQualityCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_id: str
    is_valid_mobile: bool
    is_valid_email: bool
    is_valid_voter_card: bool
    has_required_fields: bool
    is_area_booth_mismatch: bool
    is_suspicious_repeated: bool
    quality_percentage: float
    validation_issues_json: Optional[str] = None


class DataSubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    election_id: Optional[str] = None
    volunteer_id: Optional[str] = None
    volunteer_name: Optional[str] = None
    constituency_id: Optional[str] = None
    ward_id: Optional[str] = None
    booth_id: Optional[str] = None
    area_id: Optional[str] = None
    voter_id: Optional[str] = None
    
    citizen_name: str
    mobile: Optional[str] = None
    email: Optional[str] = None
    voter_card_number: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    address_line: Optional[str] = None
    ward_no: Optional[str] = None
    booth_no: Optional[str] = None
    preferred_party_candidate: Optional[str] = None
    issues_concerns: Optional[str] = None
    custom_fields_json: Optional[str] = None
    
    status: SubmissionStatus
    quality_score: float
    is_flagged_duplicate: bool
    submission_channel: str
    
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_remarks: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    quality_check: Optional[DataQualityCheckOut] = None


class DataReviewRequest(BaseModel):
    action: ReviewAction # APPROVE, REJECT, MERGE, FLAG_DUPLICATE
    remarks: Optional[str] = None
    reason: Optional[str] = None


class BulkReviewRequest(BaseModel):
    submission_ids: List[str]
    action: ReviewAction # APPROVE or REJECT
    remarks: Optional[str] = None
    reason: Optional[str] = None


class DataDuplicateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    record_a_id: str
    record_b_id: str
    match_signal: DuplicateSignal
    similarity_score: float
    match_reason: str
    resolution_status: DuplicateResolutionStatus
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    record_a: Optional[DataSubmissionOut] = None
    record_b: Optional[DataSubmissionOut] = None


class DuplicateResolveRequest(BaseModel):
    duplicate_id: str
    action: DuplicateResolutionStatus # MERGED, KEPT_SEPARATE, REJECTED
    primary_record_id: Optional[str] = None # if merging
    resolution_notes: Optional[str] = None


class DataQualityStatsOut(BaseModel):
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    incomplete_records: int
    approved_records: int
    pending_records: int
    rejected_records: int
    data_quality_percentage: float
    duplicate_percentage: float
    approval_percentage: float
    rejection_percentage: float
