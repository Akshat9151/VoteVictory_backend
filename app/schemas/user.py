from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None
    ward: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    organization_id: Optional[str] = None
    role_code: str = "VOLUNTEER" # SUPER_ADMIN, ADMIN, VOLUNTEER


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    ward: Optional[str] = None
    is_active: Optional[bool] = None
    organization_id: Optional[str] = None


class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class UserPasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: Optional[str] = None
    is_verified: bool
    is_superuser: bool
    mfa_enabled: bool
    last_login_at: Optional[datetime] = None
    roles: List[str] = []
    permissions: List[str] = []
    created_at: datetime


class UserRoleAssignRequest(BaseModel):
    role_codes: List[str]
