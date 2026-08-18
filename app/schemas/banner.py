from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.banner import BannerStatus


class BannerCreate(BaseModel):
    title: str
    description: Optional[str] = None
    image_url: str
    cta_text: Optional[str] = None
    cta_link: Optional[str] = None
    campaign_id: Optional[str] = None
    election_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    display_order: int = 0
    status: BannerStatus = BannerStatus.DRAFT


class BannerUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    cta_text: Optional[str] = None
    cta_link: Optional[str] = None
    campaign_id: Optional[str] = None
    election_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    display_order: Optional[int] = None
    status: Optional[BannerStatus] = None


class BannerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    election_id: Optional[str] = None
    campaign_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    image_url: str
    cta_text: Optional[str] = None
    cta_link: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    display_order: int
    status: BannerStatus
    created_at: datetime
