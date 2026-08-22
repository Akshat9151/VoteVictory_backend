with open('app/services/auth_service.py', 'r') as f:
    content = f.read()

import re

if 'def authenticate_google' not in content:
    new_method = '''
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
'''
    # insert before refresh_access_token
    content = content.replace('    async def refresh_access_token(', new_method + '\n    async def refresh_access_token(')
    with open('app/services/auth_service.py', 'w') as f:
        f.write(content)
