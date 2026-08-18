from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.election import ElectionStatus, ElectionType, ElectionVisibility


class ElectionSettingBase(BaseModel):
    allow_electronic_voting: bool = True
    require_voter_mfa: bool = False
    require_photo_id: bool = False
    allow_abstain: bool = True
    result_publication_policy: str = "MANUAL_APPROVAL"
    notification_rules_json: Optional[str] = None


class ElectionSettingUpdate(ElectionSettingBase):
    pass


class ElectionSettingResponse(ElectionSettingBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    election_id: str


class ElectionBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    election_type: ElectionType = ElectionType.LOCAL
    timezone: str = "UTC"
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    visibility: ElectionVisibility = ElectionVisibility.PRIVATE


class ElectionCreate(ElectionBase):
    organization_id: Optional[str] = None
    settings: Optional[ElectionSettingBase] = None


class ElectionUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    election_type: Optional[ElectionType] = None
    timezone: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    visibility: Optional[ElectionVisibility] = None


class LifecycleTransitionRequest(BaseModel):
    target_status: ElectionStatus
    reason: Optional[str] = None


class ElectionResponse(ElectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    status: ElectionStatus
    created_by: Optional[str] = None
    settings: Optional[ElectionSettingResponse] = None
    created_at: datetime
    updated_at: datetime
