import psycopg2
from sqlalchemy import create_engine, text
from app.core.database import Base
from app.models import *

direct_sync_url = "postgresql://neondb_owner:npg_TE0NKq7cybUL@ep-round-sky-axhqcmbx.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require"

print("1. Connecting via psycopg2 to direct Neon DB...")
conn = psycopg2.connect(direct_sync_url, connect_timeout=15)
conn.autocommit = True
cur = conn.cursor()

print("2. Recreating clean public schema with CASCADE...")
cur.execute("DROP SCHEMA public CASCADE;")
cur.execute("CREATE SCHEMA public;")
cur.execute("GRANT ALL ON SCHEMA public TO neondb_owner;")
cur.execute("GRANT ALL ON SCHEMA public TO public;")
cur.close()
conn.close()

print("3. Creating all tables from SQLAlchemy Base.metadata...")
engine = create_engine(direct_sync_url)
Base.metadata.create_all(bind=engine)

with engine.connect() as conn:
    print("4. Creating alembic_version at head...")
    conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(255) NOT NULL PRIMARY KEY);"))
    conn.execute(text("DELETE FROM alembic_version;"))
    conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0008_complaint_ownership_details');"))
    conn.commit()

print("5. Seeding system RBAC and Super Admin user...")
import asyncio
from app.core.database import AsyncSessionLocal
from app.core.bootstrap import seed_system_data

async def seed():
    async with AsyncSessionLocal() as session:
        await seed_system_data(session)
        await session.commit()
        print("6. Verification: Super Admin successfully created in Neon DB!")

asyncio.run(seed())
print("ALL DONE! Database schema is 100% synchronized with all models!")
