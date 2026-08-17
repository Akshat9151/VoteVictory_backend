from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.audit import record_audit_log, record_security_event
from app.core.config import settings
from app.core.exceptions import (
    AccountLockedException,
    AuthenticationException,
    MFARequiredException,
    ResourceNotFoundException,
)
from app.models.audit import SecuritySeverity
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_recovery_codes,
    generate_totp_secret,
    get_password_hash,
    get_totp_uri,
    hash_token,
    verify_password,
    verify_totp,
)
from app.models.user import User, UserSession
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, MFASetupResponse, TokenResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def authenticate_user(self, request: Request, login_data: LoginRequest) -> TokenResponse:
        user = await self.user_repo.get_by_email(login_data.email)
        
        # Security mitigation: Constant time / generic failure
        if not user:
            await record_security_event(
                self.db,
                request,
                event_type="FAILED_LOGIN_UNKNOWN_USER",
                severity=SecuritySeverity.LOW,
                details={"email": login_data.email}
            )
            raise AuthenticationException("Invalid email or password.")

        # Check account lockout
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            await record_security_event(
                self.db,
                request,
                event_type="LOCKED_ACCOUNT_LOGIN_ATTEMPT",
                severity=SecuritySeverity.MEDIUM,
                user_id=user.id,
                organization_id=user.organization_id,
                details={"locked_until": user.locked_until.isoformat()}
            )
            raise AccountLockedException(unlock_time=user.locked_until.isoformat())

        # Verify password
        if not verify_password(login_data.password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
                await record_security_event(
                    self.db,
                    request,
                    event_type="ACCOUNT_LOCKED_MAX_ATTEMPTS",
                    severity=SecuritySeverity.HIGH,
                    user_id=user.id,
                    organization_id=user.organization_id,
                    details={"failed_attempts": user.failed_login_attempts}
                )
            await self.user_repo.update(user)
            raise AuthenticationException("Invalid email or password.")

        # MFA Verification if enabled
        if user.mfa_enabled:
            if not login_data.mfa_code:
                # Generate temporary token for step-up MFA
                temp_token = create_access_token(
                    subject=user.id,
                    organization_id=user.organization_id,
                    role="MFA_PENDING",
                    expires_delta=timedelta(minutes=5)
                )
                raise MFARequiredException(temp_token=temp_token)
            
            if not verify_totp(user.mfa_secret, login_data.mfa_code):
                await record_security_event(
                    self.db,
                    request,
                    event_type="MFA_VERIFICATION_FAILED",
                    severity=SecuritySeverity.MEDIUM,
                    user_id=user.id,
                    organization_id=user.organization_id
                )
                raise AuthenticationException("Invalid MFA TOTP verification code.")

        # Reset failed login count and lockout on successful auth
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        await self.user_repo.update(user)

        # Build permissions list
        permissions = set()
        user_role_names = []
        for ur in user.roles:
            role = ur.role
            user_role_names.append(role.code)
            for rp in role.permissions:
                permissions.add(rp.permission.code)

        primary_role = user_role_names[0] if user_role_names else "VOLUNTEER"

        # Generate JWT Access & Refresh Tokens
        access_token = create_access_token(
            subject=user.id,
            organization_id=user.organization_id,
            role=primary_role,
            permissions=list(permissions)
        )
        raw_refresh, token_hash = create_refresh_token(subject=user.id)

        # Store refresh session
        session = UserSession(
            user_id=user.id,
            refresh_token_hash=token_hash,
            device_info=login_data.device_info,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            last_active_at=datetime.now(timezone.utc)
        )
        await self.user_repo.create_session(session)

        # Record audit log
        await record_audit_log(
            self.db,
            request,
            action="auth.login",
            resource_type="user",
            resource_id=user.id,
            current_user=user,
            is_success=True
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "organization_id": user.organization_id,
                "roles": user_role_names,
                "permissions": list(permissions),
                "is_superuser": user.is_superuser,
                "mfa_enabled": user.mfa_enabled
            }
        )

    async def refresh_access_token(self, request: Request, refresh_token: str) -> TokenResponse:
        token_hash = hash_token(refresh_token)
        session = await self.user_repo.get_session_by_hash(token_hash)
        
        if not session or session.is_revoked or session.expires_at < datetime.now(timezone.utc):
            await record_security_event(
                self.db,
                request,
                event_type="INVALID_REFRESH_TOKEN_ATTEMPT",
                severity=SecuritySeverity.MEDIUM
            )
            raise AuthenticationException("Invalid, expired, or revoked refresh token.")

        # Rotate refresh token
        session.is_revoked = True
        await self.user_repo.update(session)

        user = await self.user_repo.get_with_roles(session.user_id)
        if not user or not user.is_active:
            raise AuthenticationException("User account is inactive or deleted.")

        # Issue new pair
        permissions = set()
        user_role_names = []
        for ur in user.roles:
            role = ur.role
            user_role_names.append(role.code)
            for rp in role.permissions:
                permissions.add(rp.permission.code)

        primary_role = user_role_names[0] if user_role_names else "VOLUNTEER"
        new_access_token = create_access_token(
            subject=user.id,
            organization_id=user.organization_id,
            role=primary_role,
            permissions=list(permissions)
        )
        new_raw_refresh, new_token_hash = create_refresh_token(subject=user.id)

        new_session = UserSession(
            user_id=user.id,
            refresh_token_hash=new_token_hash,
            device_info=session.device_info,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            last_active_at=datetime.now(timezone.utc)
        )
        await self.user_repo.create_session(new_session)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "organization_id": user.organization_id,
                "roles": user_role_names,
                "permissions": list(permissions),
                "is_superuser": user.is_superuser
            }
        )

    async def setup_mfa(self, current_user: User) -> MFASetupResponse:
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, current_user.email)
        recovery_codes = generate_recovery_codes()

        current_user.mfa_secret = secret
        # Note: MFA remains un-enabled until user performs initial verification code confirmation
        await self.user_repo.update(current_user)

        return MFASetupResponse(
            secret=secret,
            provisioning_uri=uri,
            recovery_codes=recovery_codes
        )

    async def confirm_mfa(self, current_user: User, totp_code: str) -> bool:
        if not current_user.mfa_secret:
            raise AuthenticationException("MFA secret has not been generated for this account.")

        if not verify_totp(current_user.mfa_secret, totp_code):
            raise AuthenticationException("Invalid verification code.")

        current_user.mfa_enabled = True
        await self.user_repo.update(current_user)
        return True

    async def revoke_session(self, refresh_token: str) -> None:
        token_hash = hash_token(refresh_token)
        session = await self.user_repo.get_session_by_hash(token_hash)
        if session:
            session.is_revoked = True
            await self.user_repo.update(session)
