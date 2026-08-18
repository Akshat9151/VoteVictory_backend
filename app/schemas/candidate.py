from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.candidate import CandidateStatus


class CandidateDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_type: str
    file_name: str
    file_url: str
    verification_status: str
    created_at: Optional[datetime] = None


class CandidateBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    name: Optional[str] = None
    hindiName: Optional[str] = None
    post: Optional[str] = None
    postType: Optional[str] = "sarpanch"
    constituency: Optional[str] = None
    symbol: Optional[str] = "🚜"
    symbolName: Optional[str] = "Tractor"
    photo: Optional[str] = None
    slogan: Optional[str] = None
    votersCount: Optional[int] = 0
    volunteersCount: Optional[int] = 0
    manifesto: Optional[str] = None

    full_name: Optional[str] = None
    candidate_id_number: Optional[str] = None
    party_name: Optional[str] = None
    party_symbol_url: Optional[str] = None
    photo_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    display_order: Optional[int] = 0

    def __init__(self, **data):
        # Sync name <-> full_name
        if "name" in data and not data.get("full_name"):
            data["full_name"] = data["name"]
        elif "full_name" in data and not data.get("name"):
            data["name"] = data["full_name"]

        # Sync photo <-> photo_url
        if "photo" in data and not data.get("photo_url"):
            data["photo_url"] = data["photo"]
        elif "photo_url" in data and not data.get("photo"):
            data["photo"] = data["photo_url"]

        # Sync symbol <-> party_symbol_url
        if "symbol" in data and not data.get("party_symbol_url"):
            data["party_symbol_url"] = data["symbol"]

        super().__init__(**data)


class CandidateCreate(CandidateBase):
    election_id: Optional[str] = None
    position_id: Optional[str] = None
    constituency_id: Optional[str] = None


class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    hindiName: Optional[str] = None
    post: Optional[str] = None
    postType: Optional[str] = None
    constituency: Optional[str] = None
    symbol: Optional[str] = None
    symbolName: Optional[str] = None
    photo: Optional[str] = None
    slogan: Optional[str] = None
    votersCount: Optional[int] = None
    volunteersCount: Optional[int] = None
    manifesto: Optional[str] = None
    full_name: Optional[str] = None
    candidate_id_number: Optional[str] = None
    party_name: Optional[str] = None
    party_symbol_url: Optional[str] = None
    photo_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    display_order: Optional[int] = None
    position_id: Optional[str] = None
    constituency_id: Optional[str] = None


class CandidateStatusUpdateRequest(BaseModel):
    status: CandidateStatus
    rejection_reason: Optional[str] = None


CandidateStatusUpdate = CandidateStatusUpdateRequest


class CandidateResponse(CandidateBase):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: str
    organization_id: Optional[str] = None
    election_id: Optional[str] = None
    position_id: Optional[str] = None
    constituency_id: Optional[str] = None
    status: Optional[CandidateStatus] = CandidateStatus.APPROVED
    rejection_reason: Optional[str] = None
    approved_by: Optional[str] = None
    documents: List[CandidateDocumentResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
