from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ComplaintBase(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    ward: Optional[str] = None
    ward_name: Optional[str] = None
    category: str = "INFRASTRUCTURE"  # INFRASTRUCTURE, CORRUPTION, Water Supply, Health / School, etc.
    desc: Optional[str] = None
    description: Optional[str] = None
    reported_by_name: Optional[str] = None
    reported_by_phone: Optional[str] = None
    status: Optional[str] = "Open"  # Open, In Progress, Resolved


class ComplaintCreate(ComplaintBase):
    election_id: Optional[str] = None


class ComplaintStatusUpdate(BaseModel):
    status: str  # Open, In Progress, Resolved, OPEN, IN_PROGRESS, RESOLVED


class ComplaintUpdate(ComplaintBase):
    pass


class ComplaintResponse(BaseModel):
    id: str
    organization_id: Optional[str] = None
    election_id: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    ward: Optional[str] = None
    ward_name: Optional[str] = None
    category: str
    desc: Optional[str] = None
    description: Optional[str] = None
    reported_by_name: Optional[str] = None
    reported_by_phone: Optional[str] = None
    submitted_by_name: Optional[str] = None
    submitted_by_user_id: Optional[str] = None
    date: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
