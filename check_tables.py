import asyncio
from sqlalchemy import text
from app.core.database import async_engine

async def check_schema():
    async with async_engine.begin() as conn:
        # Get list of tables
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
        tables = [row[0] for row in result.fetchall()]
        print('Tables in database:')
        for t in tables:
            if not t.startswith('sqlite_'):
                print(f'  ✓ {t}')
        
        # Check for critical tables
        required = ['users', 'roles', 'permissions', 'user_roles']
        print('\nCritical RBAC tables:')
        for table in required:
            if table in tables:
                print(f'  ✓ {table}')
            else:
                print(f'  ❌ MISSING: {table}')

asyncio.run(check_schema())
