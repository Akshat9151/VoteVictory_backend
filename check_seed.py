import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User, Role, Permission

async def check_seed_data():
    async with AsyncSessionLocal() as session:
        # Check roles
        roles = await session.execute(select(Role).order_by(Role.code))
        role_list = roles.scalars().all()
        print(f'Roles ({len(role_list)}):')
        for role in role_list:
            print(f'  ✓ {role.code}')
        
        # Check permissions
        perms = await session.execute(select(Permission).limit(5))
        perm_list = perms.scalars().all()
        print(f'\nPermissions (sample):')
        for perm in perm_list:
            print(f'  ✓ {perm.code}')
        
        # Check super admin user
        admin = await session.execute(select(User).where(User.email == 'superadmin@electwin.com'))
        admin_user = admin.scalars().first()
        
        if admin_user:
            print(f'\n✓ Super Admin exists:')
            print(f'  Email: {admin_user.email}')
            print(f'  Name: {admin_user.first_name} {admin_user.last_name}')
            print(f'  Is Superuser: {admin_user.is_superuser}')
            print(f'  Roles: {[r.role.code for r in admin_user.roles]}')
        else:
            print(f'\n❌ Super Admin NOT found at superadmin@electwin.com')
            
            # List all users
            users = await session.execute(select(User))
            all_users = users.scalars().all()
            print(f'\nAll users in database ({len(all_users)}):')
            for user in all_users:
                print(f'  - {user.email}')

asyncio.run(check_seed_data())
