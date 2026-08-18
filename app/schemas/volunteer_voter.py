from typing import Optional
from pydantic import BaseModel, ConfigDict


class VolunteerVoterBase(BaseModel):
    name: str
    age: int
    mobile: Optional[str] = ""
    house: Optional[str] = ""
    status: Optional[str] = "Pending"  # Visited, Called, Pending, Not Reachable
    slipHanded: Optional[bool] = False


class VolunteerVoterCreate(VolunteerVoterBase):
    pass


class VolunteerVoterStatusUpdate(BaseModel):
    status: str  # Visited, Called, Pending, Not Reachable
    slipHanded: Optional[bool] = None


class VolunteerVoterResponse(VolunteerVoterBase):
    id: str

    model_config = ConfigDict(from_attributes=True)
