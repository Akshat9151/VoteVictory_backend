from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.polling_station import PollingStationStatus


class PollingStationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    address: str = Field(..., min_length=5)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity: int = Field(default=1000, ge=1)
    operating_hours: str = "08:00 - 18:00"
    status: PollingStationStatus = PollingStationStatus.ACTIVE


class PollingStationCreate(PollingStationBase):
    election_id: str
    constituency_id: Optional[str] = None


class PollingStationUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity: Optional[int] = None
    operating_hours: Optional[str] = None
    status: Optional[PollingStationStatus] = None
    constituency_id: Optional[str] = None


class PollingStationStatusUpdate(BaseModel):
    status: PollingStationStatus


class PollingStationResponse(PollingStationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    election_id: str
    constituency_id: Optional[str] = None
    assigned_volunteers_count: int = 0
    total_registered_voters: int = 0
    checked_in_voters: int = 0
    created_at: datetime
