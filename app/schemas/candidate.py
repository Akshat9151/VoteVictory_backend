from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.candidate import CandidateStatus


class CandidateDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_type: str
    file_name: str
    file_url: str
    verification_status: str
    created_at: datetime


class CandidateBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    candidate_id_number: Optional[str] = None
    party_name: Optional[str] = None
    party_symbol_url: Optional[str] = None
    photo_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    manifesto: Optional[str] = None
    display_order: int = 0


class CandidateCreate(CandidateBase):
    election_id: str
    position_id: str
    constituency_id: Optional[str] = None


class CandidateUpdate(BaseModel):
    full_name: Optional[str] = None
    candidate_id_number: Optional[str] = None
    party_name: Optional[str] = None
    party_symbol_url: Optional[str] = None
    photo_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    manifesto: Optional[str] = None
    display_order: Optional[int] = None
    position_id: Optional[str] = None
    constituency_id: Optional[str] = None


class CandidateStatusUpdateRequest(BaseModel):
    status: CandidateStatus
    rejection_reason: Optional[str] = None


class CandidateResponse(CandidateBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    election_id: str
    position_id: str
    constituency_id: Optional[str] = None
    status: CandidateStatus
    rejection_reason: Optional[str] = None
    approved_by: Optional[str] = None
    documents: List[CandidateDocumentResponse] = []
    created_at: datetime
    updated_at: datetime
