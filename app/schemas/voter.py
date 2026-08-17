from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.voter import VoterStatus, VotingStatus


class VoterBase(BaseModel):
    voter_id_number: str = Field(..., min_length=2, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    father_or_spouse_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    age: Optional[int] = Field(None, ge=18, le=120)
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    house_number: Optional[str] = None
    ward_name: Optional[str] = None
    notes: Optional[str] = None


class VoterCreate(VoterBase):
    election_id: str
    constituency_id: Optional[str] = None
    polling_station_id: Optional[str] = None


class VoterUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    father_or_spouse_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    house_number: Optional[str] = None
    ward_name: Optional[str] = None
    status: Optional[VoterStatus] = None
    constituency_id: Optional[str] = None
    polling_station_id: Optional[str] = None
    notes: Optional[str] = None


class VoterVerificationRequest(BaseModel):
    verification_method: str = "OTP" # OTP, ID_CARD, MANUAL
    id_document_type: Optional[str] = None
    id_document_number: Optional[str] = None


class VoterVerificationResponse(BaseModel):
    voter_id: str
    is_verified: bool
    verification_method: str
    message: str


class VoterResponse(VoterBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    election_id: str
    constituency_id: Optional[str] = None
    polling_station_id: Optional[str] = None
    status: VoterStatus
    voting_status: VotingStatus
    has_voted: bool
    voted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class VoterFilterParams(BaseModel):
    search: Optional[str] = None
    status: Optional[VoterStatus] = None
    voting_status: Optional[VotingStatus] = None
    constituency_id: Optional[str] = None
    polling_station_id: Optional[str] = None
    ward_name: Optional[str] = None
    has_voted: Optional[bool] = None
