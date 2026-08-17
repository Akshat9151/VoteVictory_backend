from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.organization import OrganizationStatus


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    settings_json: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[OrganizationStatus] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    settings_json: Optional[str] = None


class OrganizationResponse(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime
