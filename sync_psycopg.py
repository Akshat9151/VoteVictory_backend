from sqlalchemy import create_engine, text
from app.core.database import Base
from app.models import *
import psycopg2

sync_url = "postgresql://neondb_owner:npg_TE0NKq7cybUL@ep-round-sky-axhqcmbx-pooler.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require"

print("1. Connecting via psycopg2 sync engine...")
engine = create_engine(sync_url)

with engine.connect() as conn:
    print("2. Dropping public schema with CASCADE...")
    conn.execute(text("DROP SCHEMA public CASCADE;"))
    conn.execute(text("CREATE SCHEMA public;"))
    conn.execute(text("GRANT ALL ON SCHEMA public TO neondb_owner;"))
    conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
    conn.commit()
    
    print("3. Creating all tables from Base.metadata...")
    Base.metadata.create_all(bind=conn)
    conn.commit()
    
    print("4. Creating alembic_version...")
    conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(255) NOT NULL PRIMARY KEY);"))
    conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('5ba06aedc5cc');"))
    conn.commit()
    
    print("5. Verifying columns of users table...")
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users';"))
    cols = [r[0] for r in res.fetchall()]
    print("  -> NEW USERS TABLE COLUMNS:", cols)

print("6. Now running async seed_system_data...")
import asyncio
from app.core.database import async_engine, AsyncSessionLocal
from app.core.bootstrap import seed_system_data

async def seed():
    async with AsyncSessionLocal() as session:
        await seed_system_data(session)
        await session.commit()
        print("7. Seeding completed successfully!")

asyncio.run(seed())
print("ALL DONE SUCCESSFULLY!")
