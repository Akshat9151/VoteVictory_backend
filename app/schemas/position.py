from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class PositionBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    min_selections: int = Field(default=1, ge=1)
    max_selections: int = Field(default=1, ge=1)
    candidate_limit: int = Field(default=50, ge=1)
    display_order: int = 0
    is_active: bool = True


class PositionCreate(PositionBase):
    election_id: str
    constituency_id: Optional[str] = None


class PositionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    min_selections: Optional[int] = None
    max_selections: Optional[int] = None
    candidate_limit: Optional[int] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    constituency_id: Optional[str] = None


class PositionResponse(PositionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    election_id: str
    constituency_id: Optional[str] = None
    created_at: datetime
