from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.schemas.common import APIResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


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
