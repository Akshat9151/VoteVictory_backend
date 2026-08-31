import asyncio
import logging
from app.core.database import async_engine, Base
from app.core.bootstrap import seed_system_data
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

async def init_and_seed():
    logger.info("1. Dropping existing tables (clean slate)...")
    async with async_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))
        
    logger.info("2. Creating all tables from current models...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(255) NOT NULL PRIMARY KEY);"))
        await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0008_complaint_ownership_details');"))
    
    logger.info("3. Seeding templates, RBAC, and Super Admin...")
    async with AsyncSessionLocal() as session:
        try:
            await seed_system_data(session)
            await session.commit()
            logger.info("Data seeded successfully!")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error during seeding: {e}")

if __name__ == "__main__":
    asyncio.run(init_and_seed())
