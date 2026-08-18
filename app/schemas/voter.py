from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class VoterBase(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    voter_id_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    father_or_spouse_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    age: Optional[int] = Field(None, ge=1, le=120)
    gender: Optional[str] = "Male"
    ward: Optional[str] = None
    mobile: Optional[str] = ""
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    channel: Optional[str] = "WhatsApp"
    consent: Optional[str] = "Verified"
    source: Optional[str] = "Official Roll"
    status: Optional[str] = "Valid"
    house: Optional[str] = None
    address: Optional[str] = None
    house_number: Optional[str] = None
    ward_name: Optional[str] = None
    notes: Optional[str] = None

    def __init__(self, **data):
        # Sync id <-> voter_id_number
        if "id" in data and not data.get("voter_id_number"):
            data["voter_id_number"] = data["id"]
        elif "voter_id_number" in data and not data.get("id"):
            data["id"] = data["voter_id_number"]

        # Sync name <-> first_name / last_name
        if "name" in data and data["name"] and not data.get("first_name"):
            parts = data["name"].split(" ", 1)
            data["first_name"] = parts[0]
            data["last_name"] = parts[1] if len(parts) > 1 else ""
        elif ("first_name" in data or "last_name" in data) and not data.get("name"):
            data["name"] = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()

        # Sync mobile <-> phone_number
        if "mobile" in data and not data.get("phone_number"):
            data["phone_number"] = data["mobile"]
        elif "phone_number" in data and not data.get("mobile"):
            data["mobile"] = data["phone_number"]

        # Sync ward <-> ward_name
        if "ward" in data and not data.get("ward_name"):
            data["ward_name"] = data["ward"]
        elif "ward_name" in data and not data.get("ward"):
            data["ward"] = data["ward_name"]

        super().__init__(**data)


class VoterCreate(VoterBase):
    election_id: Optional[str] = None
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
    status: Optional[str] = None
    constituency_id: Optional[str] = None
    polling_station_id: Optional[str] = None
    notes: Optional[str] = None


class VoterVerificationRequest(BaseModel):
    verification_method: str = "OTP"
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
    organization_id: Optional[str] = None
    election_id: Optional[str] = None
    constituency_id: Optional[str] = None
    polling_station_id: Optional[str] = None
    status: Optional[str] = "Valid"
    voting_status: Optional[str] = "ELIGIBLE"
    has_voted: Optional[bool] = False
    voted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class VoterFilterParams(BaseModel):
    search: Optional[str] = None
    status: Optional[str] = None
    voting_status: Optional[str] = None
    constituency_id: Optional[str] = None
    polling_station_id: Optional[str] = None
    ward_name: Optional[str] = None
    has_voted: Optional[bool] = None


class AudienceSplit(BaseModel):
    total: int
    whatsapp: int
    sms: int
    whatsappPercent: int
    smsPercent: int


class OcrStagedRow(BaseModel):
    id: str
    epicNo: str
    name: str
    relativeName: str
    age: int
    gender: str
    houseNo: str
    mobile: str
    confidence: float
