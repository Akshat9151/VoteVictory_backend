from typing import List, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    mfa_code: Optional[str] = Field(None, description="6-digit TOTP / OTP code if MFA is enabled")
    device_info: Optional[str] = "Web Browser"


class AuthUserProfile(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = "superadmin"
    phone: Optional[str] = None
    ward: Optional[str] = None
    organization_id: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
    is_superuser: bool = False
    mfa_enabled: bool = False

    def __getitem__(self, item):
        return getattr(self, item)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token: Optional[str] = None
    email: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = 3600
    user: Optional[AuthUserProfile] = None

    def __init__(self, **data):
        if "token" not in data and "access_token" in data:
            data["token"] = data["access_token"]
        if "access_token" not in data and "token" in data:
            data["access_token"] = data["token"]
        if "user" in data and isinstance(data["user"], dict):
            data["user"] = AuthUserProfile(**data["user"])
        if data.get("email") is None and data.get("user") is not None:
            data["email"] = data["user"].email
        super().__init__(**data)


LoginResponse = TokenResponse


class TokenPayload(BaseModel):
    sub: str
    org_id: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
    exp: int


class UserRegisterRequest(BaseModel):
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    email: str
    password: str = Field(..., min_length=6)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None

    def __init__(self, **data):
        # Support camelCase fullName or snake_case full_name
        full = data.get("full_name") or data.get("fullName")
        if full:
            data["full_name"] = full
            parts = full.strip().split()
            if not data.get("first_name"):
                data["first_name"] = parts[0] if parts else "User"
            if not data.get("last_name"):
                data["last_name"] = " ".join(parts[1:]) if len(parts) > 1 else ""
        if not data.get("first_name"):
            data["first_name"] = data.get("email", "").split("@")[0] or "User"
        if not data.get("last_name"):
            data["last_name"] = ""
        super().__init__(**data)


class SignupOtpRequest(UserRegisterRequest):
    pass


class OtpVerifyRequest(BaseModel):
    challenge_id: str
    code: str = Field(..., min_length=6, max_length=6)


class OtpChallengeResponse(BaseModel):
    challenge_id: str
    destination: str
    expires_in: int
    dev_code: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    recovery_codes: List[str]


class MFAVerifyRequest(BaseModel):
    totp_code: str = Field(..., min_length=6, max_length=8)


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)
