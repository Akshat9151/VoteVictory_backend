from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    GoogleAuthRequest,
    LoginRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    OtpChallengeResponse,
    OtpVerifyRequest,
    RefreshTokenRequest,
    SignupOtpRequest,
    TokenResponse,
    UserRegisterRequest,
)
from app.schemas.common import APIResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def serialize_user(user: User) -> UserResponse:
    roles = []
    permissions = []
    if "roles" in user.__dict__ and user.__dict__["roles"]:
        for ur in user.__dict__["roles"]:
            r = getattr(ur, "role", None)
            if r:
                roles.append(r.code)
                perms = getattr(r, "permissions", None)
                if perms:
                    for rp in perms:
                        p = getattr(rp, "permission", None)
                        if p:
                            permissions.append(p.code)

    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        organization_id=user.organization_id,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        mfa_enabled=user.mfa_enabled,
        last_login_at=user.last_login_at,
        roles=roles,
        permissions=list(set(permissions)),
        created_at=user.created_at,
    )


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    token_response = await service.authenticate_user(request, login_data)
    return APIResponse(
        success=True,
        message="Authentication successful.",
        data=token_response
    )


@router.post("/register", response_model=APIResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
@router.post("/signup", response_model=APIResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    reg_data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Public user onboarding and campaign account registration."""
    service = AuthService(db)
    token_response = await service.onboard_user(request, reg_data)
    return APIResponse(
        success=True,
        message="Workspace and Super Admin account created.",
        data=token_response
    )


@router.post("/signup/request-otp", response_model=APIResponse[OtpChallengeResponse])
async def request_signup_otp(data: SignupOtpRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    challenge = await service.request_signup_otp(data)
    return APIResponse(success=True, message="Verification code sent.", data=challenge)


@router.post("/signup/verify-otp", response_model=APIResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
async def verify_signup_otp(request: Request, data: OtpVerifyRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.verify_signup_otp(request, data.challenge_id, data.code)
    return APIResponse(success=True, message="Account created and signed in successfully!", data=result)



@router.post("/login/request-otp", response_model=APIResponse[OtpChallengeResponse])
async def request_login_otp(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    challenge = await service.request_login_otp(data.email or "", data.password or "")
    return APIResponse(success=True, message="Verification code sent.", data=challenge)


@router.post("/login/verify-otp", response_model=APIResponse[TokenResponse])
async def verify_login_otp(request: Request, data: OtpVerifyRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    token_response = await service.verify_login_otp(request, data.challenge_id, data.code)
    return APIResponse(success=True, message="Authentication successful.", data=token_response)


@router.post("/forgot-password", response_model=APIResponse[OtpChallengeResponse])
@router.post("/forgot-password/request-otp", response_model=APIResponse[OtpChallengeResponse])
async def forgot_password(
    data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """Initiate password recovery with instant email OTP."""
    service = AuthService(db)
    challenge = await service.request_forgot_password_otp(data.email)
    return APIResponse(
        success=True,
        message="Password reset verification code sent to your email.",
        data=challenge
    )


@router.post("/reset-password", response_model=APIResponse[bool])
async def reset_password(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """Confirm password reset with OTP code."""
    from app.core.exceptions import AuthenticationException
    service = AuthService(db)
    challenge_id = data.challenge_id or data.token
    if challenge_id and data.code:
        await service.reset_password_with_otp(challenge_id, data.code, data.new_password)
    elif data.token:
        await service.reset_password(data.token, data.new_password)
    else:
        raise AuthenticationException("Verification code is required.")
    return APIResponse(
        success=True,
        message="Password updated successfully. Please log in with your new password.",
        data=True
    )



@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh_token(
    request: Request,
    refresh_in: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    token_response = await service.refresh_access_token(request, refresh_in.refresh_token)
    return APIResponse(
        success=True,
        message="Token successfully refreshed.",
        data=token_response
    )


@router.post("/logout", response_model=APIResponse[bool])
async def logout(
    refresh_in: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    await service.revoke_session(refresh_in.refresh_token)
    return APIResponse(success=True, message="Session successfully revoked.", data=True)


@router.post("/mfa/setup", response_model=APIResponse[MFASetupResponse])
async def setup_mfa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    mfa_data = await service.setup_mfa(current_user)
    return APIResponse(
        success=True,
        message="MFA secret generated. Scan QR code and confirm with a TOTP token.",
        data=mfa_data
    )


@router.post("/mfa/confirm", response_model=APIResponse[bool])
async def confirm_mfa(
    verify_in: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    success = await service.confirm_mfa(current_user, verify_in.totp_code)
    return APIResponse(success=True, message="MFA successfully activated.", data=success)

@router.post("/google", response_model=APIResponse[TokenResponse])
async def google_auth(
    request: Request,
    data: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    token_response = await service.authenticate_google(request, data.credential)
    return APIResponse(
        success=True,
        message="Google authentication successful.",
        data=token_response
    )
