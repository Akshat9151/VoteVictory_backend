import psycopg2
from sqlalchemy import create_engine, text
from app.core.database import Base
from app.models import *

direct_sync_url = "postgresql://neondb_owner:npg_TE0NKq7cybUL@ep-round-sky-axhqcmbx.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require"

print("1. Connecting to direct Neon endpoint with psycopg2...")
engine = create_engine(direct_sync_url)

with engine.connect() as conn:
    print("2. Dropping public schema with CASCADE...")
    conn.execute(text("DROP SCHEMA public CASCADE;"))
    conn.execute(text("CREATE SCHEMA public;"))
    conn.execute(text("GRANT ALL ON SCHEMA public TO neondb_owner;"))
    conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
    conn.commit()
    
    print("3. Creating all tables from SQLAlchemy models...")
    Base.metadata.create_all(bind=conn)
    conn.commit()
    
    print("4. Initializing alembic_version table...")
    conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(255) NOT NULL PRIMARY KEY);"))
    conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('5ba06aedc5cc');"))
    conn.commit()
    
    print("5. Checking columns in newly created users table...")
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users';"))
    cols = [r[0] for r in res.fetchall()]
    print("  -> NEW USERS COLUMNS:", cols)

print("6. Now seeding initial Super Admin & system RBAC...")
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.bootstrap import seed_system_data

direct_async_url = "postgresql+asyncpg://neondb_owner:npg_TE0NKq7cybUL@ep-round-sky-axhqcmbx.c-4.us-east-2.aws.neon.tech/neondb?ssl=require"

async def async_seed():
    async_eng = create_async_engine(direct_async_url)
    session_factory = async_sessionmaker(bind=async_eng, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await seed_system_data(session)
        await session.commit()
        print("7. Seeding completed successfully!")
    await async_eng.dispose()

asyncio.run(async_seed())
print("ALL DONE! Neon database is 100% synced with correct schema and seeded Super Admin!")
