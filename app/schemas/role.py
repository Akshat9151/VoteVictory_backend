from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    module: str
    description: Optional[str] = None


class RoleBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None


class RoleCreate(RoleBase):
    organization_id: Optional[str] = None
    permission_codes: List[str] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_codes: Optional[List[str]] = None


class RoleResponse(RoleBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: Optional[str] = None
    is_system: bool
    permissions: List[str] = []
    created_at: datetime
