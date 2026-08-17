import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.permissions import DEFAULT_ROLE_PERMISSIONS, PermissionCode, RoleCode
from app.core.security import get_password_hash
from app.models.user import Permission, Role, RolePermission, User, UserRole

logger = logging.getLogger("app.bootstrap")


async def seed_system_data(db: AsyncSession) -> None:
    """Seeds initial permissions, roles, and default Super Admin if not present."""
    # 1. Seed Permissions
    existing_perms = set((await db.execute(select(Permission.code))).scalars().all())
    for perm_code in PermissionCode:
        code_str = perm_code.value
        if code_str not in existing_perms:
            module_name = code_str.split(".")[0] if "." in code_str else "system"
            perm = Permission(
                code=code_str,
                name=code_str.replace(".", " ").replace("_", " ").title(),
                module=module_name,
                description=f"Permission to perform {code_str} actions"
            )
            db.add(perm)
    await db.flush()

    # Query all permissions mapped by code
    all_perms_map = {
        p.code: p
        for p in (await db.execute(select(Permission))).scalars().all()
    }

    # 2. Seed System Roles & Role Permissions
    for role_code, perm_enums in DEFAULT_ROLE_PERMISSIONS.items():
        stmt = select(Role).where(Role.code == role_code.value, Role.is_system == True)
        role = (await db.execute(stmt)).scalars().first()
        if not role:
            role = Role(
                name=role_code.value.replace("_", " ").title(),
                code=role_code.value,
                is_system=True,
                description=f"Standard system role for {role_code.value}"
            )
            db.add(role)
            await db.flush()

            # Attach permissions
            for p_enum in perm_enums:
                perm_obj = all_perms_map.get(p_enum.value)
                if perm_obj:
                    rp = RolePermission(role_id=role.id, permission_id=perm_obj.id)
                    db.add(rp)
            await db.flush()

    # 3. Seed First Super Admin
    admin_email = settings.FIRST_SUPER_ADMIN_EMAIL.lower().strip()
    admin_stmt = select(User).where(User.email == admin_email)
    existing_admin = (await db.execute(admin_stmt)).scalars().first()

    if not existing_admin:
        logger.info(f"Bootstrapping default Super Admin: {admin_email}")
        super_admin = User(
            email=admin_email,
            first_name=settings.FIRST_SUPER_ADMIN_FIRST_NAME,
            last_name=settings.FIRST_SUPER_ADMIN_LAST_NAME,
            password_hash=get_password_hash(settings.FIRST_SUPER_ADMIN_PASSWORD),
            is_active=True,
            is_verified=True,
            is_superuser=True
        )
        db.add(super_admin)
        await db.flush()

        # Assign SUPER_ADMIN role
        super_role_stmt = select(Role).where(Role.code == RoleCode.SUPER_ADMIN.value)
        super_role = (await db.execute(super_role_stmt)).scalars().first()
        if super_role:
            ur = UserRole(user_id=super_admin.id, role_id=super_role.id)
            db.add(ur)
        await db.flush()
        logger.info("Super Admin bootstrap complete.")
