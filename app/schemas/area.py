from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.area import BoothStatus, MapStatus


class WardCreate(BaseModel):
    constituency_id: str
    ward_number: str
    name: str
    description: Optional[str] = None


class WardUpdate(BaseModel):
    ward_number: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None


class WardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    constituency_id: str
    ward_number: str
    name: str
    description: Optional[str] = None
    created_at: datetime


class BoothCreate(BaseModel):
    constituency_id: str
    ward_id: Optional[str] = None
    booth_number: str
    name: str
    location_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    target: int = 1000


class BoothUpdate(BaseModel):
    ward_id: Optional[str] = None
    booth_number: Optional[str] = None
    name: Optional[str] = None
    location_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    target: Optional[int] = None
    status: Optional[BoothStatus] = None


class BoothOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    constituency_id: str
    ward_id: Optional[str] = None
    booth_number: str
    name: str
    location_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    target: int
    collected_count: int
    achievement_percentage: float = 0.0
    status: BoothStatus
    created_at: datetime


class BoothStatsOut(BaseModel):
    booth_id: str
    booth_number: str
    booth_name: str
    target: int
    collected: int
    achievement_percentage: float
    active_volunteers_count: int
    pending_data_count: int


class AreaCreate(BaseModel):
    constituency_id: str
    ward_id: Optional[str] = None
    booth_id: Optional[str] = None
    state: str = "National"
    district: Optional[str] = None
    name: str
    code: Optional[str] = None
    target: int = 500
    boundary_geojson: Optional[str] = None


class AreaUpdate(BaseModel):
    ward_id: Optional[str] = None
    booth_id: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    name: Optional[str] = None
    code: Optional[str] = None
    target: Optional[int] = None
    boundary_geojson: Optional[str] = None


class AreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    constituency_id: str
    ward_id: Optional[str] = None
    booth_id: Optional[str] = None
    state: str
    district: Optional[str] = None
    name: str
    code: Optional[str] = None
    target: int
    collected_count: int
    achievement_percentage: float = 0.0
    map_status: MapStatus
    boundary_geojson: Optional[str] = None
    created_at: datetime


class MapMetricsOut(BaseModel):
    area_id: str
    area_name: str
    state: str
    district: Optional[str] = None
    target: int
    collected: int
    achievement_percentage: float
    status: MapStatus # GREEN, YELLOW, RED, GREY
    latitude: Optional[float] = None
    longitude: Optional[float] = None
