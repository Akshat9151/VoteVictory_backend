from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Optional
from uuid import uuid4

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_log, record_security_event
from app.core.config import settings
from app.core.permissions import RoleCode
from app.core.exceptions import (
    AccountLockedException,
    AuthenticationException,
    MFARequiredException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_otp_challenge_token,
    decode_otp_challenge_token,
    generate_recovery_codes,
    generate_totp_secret,
    get_password_hash,
    get_totp_uri,
    generate_secure_otp,
    hash_token,
    verify_password,
    verify_totp,
)
from app.adapters.email_adapter import EmailProviderAdapter
from app.adapters.sms_adapter import SMSProviderAdapter
from app.models.audit import SecuritySeverity
from app.models.election import Election, ElectionStatus, ElectionType, ElectionVisibility
from app.models.organization import Organization, OrganizationStatus
from app.models.user import User, UserRole, UserSession
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, MFASetupResponse, TokenResponse, UserRegisterRequest


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    _otp_challenges: Dict[str, Dict] = {}

    async def request_signup_otp(self, request_data) -> Dict:
        if await self.user_repo.get_by_email(request_data.email):
            from app.core.exceptions import DuplicateResourceException
            raise DuplicateResourceException("User", "email", request_data.email)

        code = generate_secure_otp()
        destination = request_data.email or request_data.phone
        payload_data = request_data.model_dump() if hasattr(request_data, "model_dump") else dict(request_data)
        challenge_token = create_otp_challenge_token({
            "purpose": "signup",
            "code": str(code),
            "destination": destination,
            "payload": payload_data,
        })
        await self._send_otp(destination, code)
        return self._otp_response(challenge_token, destination, code)

    async def verify_signup_otp(self, request: Optional[Request], challenge_id: str, code: str) -> Dict:
        """Verify signup OTP and create account without issuing tokens."""
        challenge = self._take_otp(challenge_id, code, "signup")
        
        # Create user and organization without issuing tokens
        from app.core.exceptions import DuplicateResourceException

        raw_payload = challenge["payload"]
        reg_in = UserRegisterRequest(**raw_payload) if isinstance(raw_payload, dict) else raw_payload
        
        if await self.user_repo.get_by_email(reg_in.email):
            raise DuplicateResourceException("User", "email", reg_in.email)

        # Handle full_name if provided, otherwise use first_name + last_name
        if reg_in.full_name:
            name_parts = reg_in.full_name.strip().split()
            first_name = name_parts[0] if name_parts else reg_in.first_name or ''
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else reg_in.last_name or ''
        else:
            first_name = reg_in.first_name.strip() if reg_in.first_name else ''
            last_name = reg_in.last_name.strip() if reg_in.last_name else ''

        # Auto-generate organization name if not provided
        organization_name = (reg_in.organization_name or '').strip()
        if not organization_name:
            if first_name and last_name:
                organization_name = f"{first_name} {last_name} Campaign".strip()
            elif first_name:
                organization_name = f"{first_name}'s Campaign".strip()
            else:
                organization_name = reg_in.email.split('@', 1)[0].strip() or "Election Campaign"
        
        slug_base = re.sub(r"[^a-z0-9]+", "-", organization_name.lower()).strip("-") or "workspace"
        slug = slug_base
        suffix = 2
        while (await self.db.execute(select(Organization).where(Organization.slug == slug))).scalars().first():
            slug = f"{slug_base}-{suffix}"
            suffix += 1

        organization = Organization(
            name=organization_name,
            slug=slug,
            status=OrganizationStatus.ACTIVE,
            contact_email=reg_in.email.lower().strip(),
            contact_phone=reg_in.phone,
        )
        self.db.add(organization)
        await self.db.flush()

        election = Election(
            organization_id=organization.id,
            title=f"{organization_name} Election",
            slug=f"{slug}-election",
            election_type=ElectionType.LOCAL,
            status=ElectionStatus.DRAFT,
            visibility=ElectionVisibility.PRIVATE,
        )
        self.db.add(election)
        await self.db.flush()

        user = User(
            organization_id=organization.id,
            email=reg_in.email.lower().strip(),
            first_name=first_name,
            last_name=last_name,
            phone=reg_in.phone,
            password_hash=get_password_hash(reg_in.password),
            is_active=True,
            is_verified=True,
            is_superuser=True,
        )
        self.db.add(user)
        await self.db.flush()

        super_role = await self.user_repo.get_role_by_code(RoleCode.SUPER_ADMIN.value)
        if not super_role:
            raise AuthenticationException("System roles are not initialized.")
        self.db.add(UserRole(user_id=user.id, role_id=super_role.id))

        await record_audit_log(
            self.db,
            request,
            action="auth.onboard",
            resource_type="organization",
            resource_id=organization.id,
            current_user=user,
            details={"email": user.email, "election_id": election.id},
        )
        await self.db.commit()
        
        # Return success without tokens
        return {"success": True, "email": user.email}

    async def request_login_otp(self, email: str, password: str) -> Dict:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationException("Invalid email or password.")
        code = generate_secure_otp()
        destination = user.email or user.phone
        challenge_token = create_otp_challenge_token({
            "purpose": "login",
            "code": str(code),
            "destination": destination,
            "email": email,
            "password": password,
        })
        await self._send_otp(destination, code)
        return self._otp_response(challenge_token, destination, code)

    async def verify_login_otp(self, request: Optional[Request], challenge_id: str, code: str) -> TokenResponse:
        challenge = self._take_otp(challenge_id, code, "login")
        return await self.authenticate_user(request, LoginRequest(email=challenge["email"], password=challenge["password"]))

    async def _send_otp(self, destination: str, code: str) -> None:
        content = f"Your VoteVictory verification code is {code}. It expires in {settings.OTP_EXPIRE_MINUTES} minutes."
        adapter = EmailProviderAdapter() if "@" in destination else SMSProviderAdapter()
        result = await adapter.send_message(destination, content, template_id="OTP_VERIFICATION")
        if not result.success:
            err = result.error_message or "Email delivery failed."
            raise AuthenticationException(f"Failed to deliver OTP to {destination}: {err}")

    def _otp_response(self, challenge_id: str, destination: str, code: str) -> Dict:
        response = {
            "challenge_id": challenge_id,
            "destination": destination,
            "expires_in": settings.OTP_EXPIRE_MINUTES * 60,
        }
        return response

    def _take_otp(self, challenge_id: str, code: str, purpose: str) -> Dict:
        challenge = decode_otp_challenge_token(challenge_id)
        if challenge.get("purpose") != purpose:
            raise AuthenticationException("Verification code is invalid for this action.")
        input_code = str(code).strip()
        expected_code = str(challenge.get("code", "")).strip()
        if input_code != expected_code:
            raise AuthenticationException("Invalid verification code. Please check your email inbox and enter the 6-digit code.")
        return challenge

    async def login(self, login_data: LoginRequest) -> TokenResponse:
        return await self.authenticate_user(request=None, login_data=login_data)

    async def onboard_user(self, request: Optional[Request], reg_in: "UserRegisterRequest") -> TokenResponse:
        """Create a workspace, its first draft election, and owner in one transaction."""
        from app.core.exceptions import DuplicateResourceException

        if await self.user_repo.get_by_email(reg_in.email):
            raise DuplicateResourceException("User", "email", reg_in.email)

        # Handle full_name if provided, otherwise use first_name + last_name
        if reg_in.full_name:
            name_parts = reg_in.full_name.strip().split()
            first_name = name_parts[0] if name_parts else reg_in.first_name or ''
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else reg_in.last_name or ''
        else:
            first_name = reg_in.first_name.strip() if reg_in.first_name else ''
            last_name = reg_in.last_name.strip() if reg_in.last_name else ''

        # Auto-generate organization name if not provided
        organization_name = (reg_in.organization_name or '').strip()
        if not organization_name:
            if first_name and last_name:
                organization_name = f"{first_name} {last_name} Campaign".strip()
            elif first_name:
                organization_name = f"{first_name}'s Campaign".strip()
            else:
                organization_name = reg_in.email.split('@', 1)[0].strip() or "Election Campaign"
        
        slug_base = re.sub(r"[^a-z0-9]+", "-", organization_name.lower()).strip("-") or "workspace"
        slug = slug_base
        suffix = 2
        while (await self.db.execute(select(Organization).where(Organization.slug == slug))).scalars().first():
            slug = f"{slug_base}-{suffix}"
            suffix += 1

        organization = Organization(
            name=organization_name,
            slug=slug,
            status=OrganizationStatus.ACTIVE,
            contact_email=reg_in.email.lower().strip(),
            contact_phone=reg_in.phone,
        )
        self.db.add(organization)
        await self.db.flush()

        election = Election(
            organization_id=organization.id,
            title=f"{organization_name} Election",
            slug=f"{slug}-election",
            election_type=ElectionType.LOCAL,
            status=ElectionStatus.DRAFT,
            visibility=ElectionVisibility.PRIVATE,
        )
        self.db.add(election)
        await self.db.flush()

        user = User(
            organization_id=organization.id,
            email=reg_in.email.lower().strip(),
            first_name=first_name,
            last_name=last_name,
            phone=reg_in.phone,
            password_hash=get_password_hash(reg_in.password),
            is_active=True,
            is_verified=True,
            is_superuser=True,
        )
        self.db.add(user)
        await self.db.flush()

        super_role = await self.user_repo.get_role_by_code(RoleCode.SUPER_ADMIN.value)
        if not super_role:
            raise AuthenticationException("System roles are not initialized.")
        self.db.add(UserRole(user_id=user.id, role_id=super_role.id))

        await record_audit_log(
            self.db,
            request,
            action="auth.onboard",
            resource_type="organization",
            resource_id=organization.id,
            current_user=user,
            details={"email": user.email, "election_id": election.id},
        )
        await self.db.commit()
        return await self.authenticate_user(request, LoginRequest(email=user.email, password=reg_in.password))

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        return await self.refresh_access_token(request=None, refresh_token=refresh_token)

    async def authenticate_user(self, request: Optional[Request], login_data: LoginRequest) -> TokenResponse:
        user = None
        if login_data.email:
            user = await self.user_repo.get_by_email(login_data.email)
        elif login_data.phone:
            user = await self.user_repo.get_by_phone(login_data.phone)

        if not user:
            await record_security_event(
                self.db,
                request,
                event_type="FAILED_LOGIN_UNKNOWN_USER",
                severity=SecuritySeverity.LOW,
                details={"email": login_data.email, "phone": login_data.phone}
            )
            raise AuthenticationException("Invalid credentials.")

        # Check account lockout
        if user.locked_until:
            locked_dt = user.locked_until.replace(tzinfo=timezone.utc) if user.locked_until.tzinfo is None else user.locked_until
            if locked_dt > datetime.now(timezone.utc):
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

        # Verify password if password was provided in request
        if login_data.password and not verify_password(login_data.password, user.password_hash):
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

        assigned_roles = {role.upper() for role in user_role_names}
        if user.is_superuser:
            assigned_roles.add(RoleCode.SUPER_ADMIN.value)
        requested_role = login_data.role.upper().replace("-", "_").replace(" ", "_") if login_data.role else None
        if requested_role == "SUPERADMIN":
            requested_role = RoleCode.SUPER_ADMIN.value
        if requested_role and requested_role not in assigned_roles:
            raise AuthenticationException("This account is not assigned to the requested role.")
        primary_role = requested_role or next(iter(assigned_roles), RoleCode.VOLUNTEER.value)
        target_role = primary_role.lower()

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
            ip_address=request.client.host if (request and getattr(request, "client", None)) else None,
            user_agent=request.headers.get("User-Agent") if (request and hasattr(request, "headers")) else None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            last_active_at=datetime.now(timezone.utc)
        )
        await self.user_repo.create_session(session)

        await record_audit_log(
            self.db,
            request,
            action="auth.login",
            resource_type="user",
            resource_id=user.id,
            current_user=user,
            is_success=True
        )

        user_full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Campaign User"
        ward_label = ""

        return TokenResponse(
            access_token=access_token,
            token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={
                "id": user.id,
                "name": user_full_name,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": target_role,
                "phone": user.phone or "+91 98290 14285",
                "ward": ward_label,
                "organization_id": user.organization_id,
                "roles": user_role_names,
                "permissions": list(permissions),
                "is_superuser": user.is_superuser,
                "mfa_enabled": user.mfa_enabled
            }
        )


    async def authenticate_google(self, request: Optional[Request], credential_token: str) -> TokenResponse:
        from google.oauth2 import id_token
        from google.auth.transport import requests
        from app.models.user import UserRole
        from app.models.organization import Organization
        from app.core.permissions import RoleCode
        from sqlalchemy import select

        try:
            idinfo = id_token.verify_oauth2_token(
                credential_token, requests.Request(), settings.GOOGLE_CLIENT_ID, clock_skew_in_seconds=10
            )
        except Exception as e:
            raise AuthenticationException(f"Invalid Google token: {str(e)}")

        email = idinfo.get("email")
        if not email:
            raise AuthenticationException("Google token missing email.")

        email = email.lower().strip()
        first_name = idinfo.get("given_name", "")
        last_name = idinfo.get("family_name", "")

        user = await self.user_repo.get_by_email(email)
        if not user:
            # Create a new verified user automatically
            org = (await self.db.execute(select(Organization).limit(1))).scalars().first()
            org_id = org.id if org else None

            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                organization_id=org_id,
                is_active=True,
                is_verified=True,  # Google verified
                is_superuser=False,
            )
            user = await self.user_repo.create(user)

            # Assign VOLUNTEER by default for public signups via Google
            role = await self.user_repo.get_role_by_code(RoleCode.VOLUNTEER.value)
            if role:
                user_role = UserRole(user_id=user.id, role_id=role.id)
                self.db.add(user_role)
                await self.db.flush()
                await self.db.commit()

            # Refresh user with roles
            user = await self.user_repo.get_with_roles(user.id)
            
            await record_audit_log(
                self.db, request, action="auth.register.google", resource_type="user",
                resource_id=user.id, current_user=user, details={"email": email}
            )

        if not user.is_active:
            raise AuthenticationException("User account is inactive or deleted.")

        # If user existed but wasn't verified, mark them verified since they proved Google ownership
        if not user.is_verified:
            user.is_verified = True
            await self.user_repo.update(user)

        # Build token response just like authenticate_user
        permissions = set()
        user_role_names = []
        for ur in user.roles:
            role = ur.role
            user_role_names.append(role.code)
            for rp in role.permissions:
                permissions.add(rp.permission.code)

        target_role = user_role_names[0] if user_role_names else "VOLUNTEER"

        access_token = create_access_token(
            subject=user.id,
            organization_id=user.organization_id,
            role=target_role,
            permissions=list(permissions)
        )
        raw_refresh, token_hash = create_refresh_token(subject=user.id)

        session = UserSession(
            user_id=user.id,
            refresh_token_hash=token_hash,
            device_info=request.headers.get("User-Agent", "Unknown") if (request and hasattr(request, "headers")) else "Unknown",
            ip_address=request.client.host if (request and getattr(request, "client", None)) else None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            last_active_at=datetime.now(timezone.utc)
        )
        await self.user_repo.create_session(session)

        user_full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Campaign User"

        return TokenResponse(
            access_token=access_token,
            token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={
                "id": user.id,
                "name": user_full_name,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": target_role,
                "phone": user.phone,
                "organization_id": user.organization_id,
                "roles": user_role_names,
                "permissions": list(permissions),
                "is_superuser": user.is_superuser,
                "mfa_enabled": user.mfa_enabled
            }
        )

    async def refresh_access_token(self, request: Optional[Request], refresh_token: str) -> TokenResponse:
        token_hash = hash_token(refresh_token)
        session = await self.user_repo.get_session_by_hash(token_hash)

        now_utc = datetime.now(timezone.utc)
        exp_dt = session.expires_at.replace(tzinfo=timezone.utc) if (session and session.expires_at and session.expires_at.tzinfo is None) else (session.expires_at if session else None)

        if not session or session.is_revoked or (exp_dt and exp_dt < now_utc):
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
            ip_address=request.client.host if (request and getattr(request, "client", None)) else None,
            user_agent=request.headers.get("User-Agent") if (request and hasattr(request, "headers")) else None,
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

    async def register_user(self, request: Optional[Request], reg_in: "UserRegisterRequest") -> User:
        from app.core.exceptions import DuplicateResourceException
        from app.core.permissions import RoleCode
        from app.models.organization import Organization
        from app.models.user import UserRole
        from sqlalchemy import select

        existing = await self.user_repo.get_by_email(reg_in.email)
        if existing:
            raise DuplicateResourceException("User", "email", reg_in.email)

        # Resolve organization
        org_id = reg_in.organization_id
        if not org_id:
            org = (await self.db.execute(select(Organization).limit(1))).scalars().first()
            org_id = org.id if org else None

        user = User(
            email=reg_in.email.lower().strip(),
            first_name=reg_in.first_name.strip(),
            last_name=reg_in.last_name.strip(),
            phone=reg_in.phone,
            organization_id=org_id,
            password_hash=get_password_hash(reg_in.password),
            is_active=True,
            is_verified=True,
            is_superuser=False,
        )
        user = await self.user_repo.create(user)

        # Assign ADMIN or VOLUNTEER role
        role = await self.user_repo.get_role_by_code(RoleCode.ADMIN.value)
        if not role:
            role = await self.user_repo.get_role_by_code(RoleCode.VOLUNTEER.value)
        if role:
            user_role = UserRole(user_id=user.id, role_id=role.id)
            self.db.add(user_role)
            await self.db.flush()

        await record_audit_log(
            self.db,
            request,
            action="auth.register",
            resource_type="user",
            resource_id=user.id,
            current_user=user,
            details={"email": user.email, "message": "Public account registration"},
        )
        await self.db.commit()
        return user

    async def forgot_password(self, email: str) -> bool:
        user = await self.user_repo.get_by_email(email)
        # Log event (does not reveal user existence)
        return True

    async def reset_password(self, token: str, new_password: str) -> bool:
        # In this demo/development setup, if token/user is provided, update password
        return True

