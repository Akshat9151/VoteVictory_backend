from typing import Optional

from pydantic import BaseModel, ConfigDict


class ComplaintBase(BaseModel):
    name: str
    ward: str
    category: str  # Water Supply, Health / School, Road Drainage, Electricity, Sanitation, Other
    desc: str
    status: Optional[str] = "Open"  # Open, In Progress, Resolved


class ComplaintCreate(ComplaintBase):
    pass


class ComplaintStatusUpdate(BaseModel):
    status: str  # Open, In Progress, Resolved


class ComplaintResponse(ComplaintBase):
    id: str
    date: str

    model_config = ConfigDict(from_attributes=True)
