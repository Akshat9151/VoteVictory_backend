from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ConstituencyBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: Optional[str] = None
    description: Optional[str] = None


class ConstituencyCreate(ConstituencyBase):
    election_id: str


class ConstituencyUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None


class ConstituencyResponse(ConstituencyBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    election_id: str
    created_at: datetime
