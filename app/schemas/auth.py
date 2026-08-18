from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    mfa_code: Optional[str] = Field(None, description="6-digit TOTP / OTP code if MFA is enabled")
    device_info: Optional[str] = "Web Browser"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int # seconds
    user: Dict[str, Any]


LoginResponse = TokenResponse


class TokenPayload(BaseModel):
    sub: str
    org_id: Optional[str] = None
    email: str
    roles: List[str] = []
    permissions: List[str] = []
    exp: int


class UserRegisterRequest(BaseModel):
    organization_id: Optional[str] = None
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str
    last_name: str
    phone: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    recovery_codes: List[str]


class MFAVerifyRequest(BaseModel):
    totp_code: str = Field(..., min_length=6, max_length=8)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)
