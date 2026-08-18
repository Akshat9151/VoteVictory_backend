from typing import Optional
from pydantic import BaseModel, ConfigDict


class TeamMemberBase(BaseModel):
    name: str
    role: str = "Volunteer"  # Super Admin, Admin, Volunteer
    roleTitle: str
    ward: str
    phone: str
    status: Optional[str] = "Active"  # Active, Inactive, Invited


class TeamMemberCreate(TeamMemberBase):
    pass


class TeamMemberResponse(TeamMemberBase):
    id: str
    votersHandled: int = 0
    addedDate: str

    model_config = ConfigDict(from_attributes=True)
