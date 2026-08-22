import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.database import Base, AsyncSessionLocal
from app.core.bootstrap import seed_system_data
from app.models import *

url = 'postgresql+asyncpg://neondb_owner:npg_TE0NKq7cybUL@ep-round-sky-axhqcmbx-pooler.c-4.us-east-2.aws.neon.tech/neondb?ssl=require'

async def sync_neon_db():
    engine = create_async_engine(url, connect_args={'statement_cache_size': 0})
    async with engine.begin() as conn:
        print('1. Checking current users table columns...')
        res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users';"))
        cols = [r[0] for r in res.fetchall()]
        print('Existing columns in users:', cols)

        print('2. Recreating tables directly from Base.metadata to match SQLAlchemy models 100%...')
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
        print('3. Stamping alembic version...')
        await conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(255) NOT NULL PRIMARY KEY);"))
        await conn.execute(text("DELETE FROM alembic_version;"))
        await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('5ba06aedc5cc');"))

    print('4. Seeding system RBAC and Super Admin user in Neon DB...')
    session = AsyncSessionLocal(bind=engine)
    try:
        await seed_system_data(session)
        await session.commit()
        print('Seeding completed successfully!')
    finally:
        await session.close()
    
    await engine.dispose()
    print('ALL DONE! Neon Database is ready and seeded!')

if __name__ == '__main__':
    asyncio.run(sync_neon_db())
