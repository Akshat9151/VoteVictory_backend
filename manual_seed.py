"""
Manual seed script to create super admin and seed data on Neon.
Run this once after migrations to ensure bootstrap data exists.
"""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.bootstrap import seed_system_data
from app.core.config import settings
from app.models.user import User

async def manual_seed():
    """Force seed system data on Neon."""
    async with AsyncSessionLocal() as session:
        # Check if super admin already exists
        admin = await session.execute(
            select(User).where(User.email == settings.FIRST_SUPER_ADMIN_EMAIL.lower().strip())
        )
        existing_admin = admin.scalars().first()
        
        if existing_admin:
            print(f"✓ Super admin already exists: {existing_admin.email}")
            return
        
        print(f"Seeding system data on {settings.DATABASE_URL}...")
        try:
            await seed_system_data(session)
            await session.commit()
            print("✓ Seed completed successfully")
            
            # Verify
            admin = await session.execute(
                select(User).where(User.email == settings.FIRST_SUPER_ADMIN_EMAIL.lower().strip())
            )
            new_admin = admin.scalars().first()
            if new_admin:
                print(f"✓ Super admin created: {new_admin.email} ({new_admin.first_name} {new_admin.last_name})")
            else:
                print("❌ Super admin creation failed verification")
        except Exception as e:
            await session.rollback()
            print(f"❌ Seed failed: {str(e)}")
            raise

if __name__ == "__main__":
    asyncio.run(manual_seed())
