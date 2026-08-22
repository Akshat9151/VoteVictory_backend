import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.database import Base, AsyncSessionLocal
from app.core.bootstrap import seed_system_data
from app.models import *

url = 'postgresql+asyncpg://neondb_owner:npg_TE0NKq7cybUL@ep-round-sky-axhqcmbx-pooler.c-4.us-east-2.aws.neon.tech/neondb?ssl=require'

async def clean_reset_neon():
    engine = create_async_engine(url, connect_args={'statement_cache_size': 0})
    
    print('1. Dropping public schema with CASCADE...')
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO neondb_owner;"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        
        print('2. Creating all tables from SQLAlchemy models...')
        await conn.run_sync(Base.metadata.create_all)
        
        print('3. Initializing alembic_version table...')
        await conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(255) NOT NULL PRIMARY KEY);"))
        await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('5ba06aedc5cc');"))

    print('4. Seeding system RBAC, templates and Super Admin user in Neon DB...')
    session = AsyncSessionLocal(bind=engine)
    try:
        await seed_system_data(session)
        await session.commit()
        print('5. Verification: Checking Super Admin in Neon DB...')
        res = await session.execute(text("SELECT id, email, first_name, last_name, is_superuser, password_hash FROM users;"))
        rows = res.fetchall()
        for r in rows:
            print('  -> USER IN DB:', r)
    finally:
        await session.close()
    
    await engine.dispose()
    print('SUCCESS! Neon database completely initialized and verified!')

if __name__ == '__main__':
    asyncio.run(clean_reset_neon())
