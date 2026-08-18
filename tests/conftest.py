import asyncio
import os
import sys

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Override configuration for test runtime
test_db_url = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ["DATABASE_URL"] = test_db_url
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-length-secure-hash!"
os.environ["ENVIRONMENT"] = "testing"

from app.core.bootstrap import seed_system_data
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.organization import Organization, OrganizationStatus
from app.models.user import RoleCode, User

# Test Async Engine
engine_kwargs = {"future": True}
if "sqlite" in test_db_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

test_engine = create_async_engine(test_db_url, **engine_kwargs)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Creates a fresh test database schema and session per test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        await seed_system_data(session)
        await session.commit()
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    """Provides an AsyncClient for FastAPI endpoint testing with DB dependency override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_org(db_session: AsyncSession) -> Organization:
    """Creates a sample test tenant organization."""
    org = Organization(
        name="Apex Electoral Commission",
        slug="apex-commission",
        contact_email="admin@apex.org",
        status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def superadmin_token(db_session: AsyncSession) -> str:
    """Generates a valid Super Admin JWT for seeded admin."""
    from sqlalchemy import select
    stmt = select(User).where(User.email == settings.FIRST_SUPER_ADMIN_EMAIL.lower().strip())
    admin = (await db_session.execute(stmt)).scalars().first()
    return create_access_token(
        subject=admin.id,
        organization_id=None,
        role=RoleCode.SUPER_ADMIN.value,
        permissions=["system.manage", "election.create", "election.view", "election.update", "voter.create", "voter.view", "result.publish", "audit.view"]
    )


@pytest_asyncio.fixture
async def admin_token(db_session: AsyncSession, test_org: Organization) -> str:
    """Creates a real Admin user and generates JWT."""
    from sqlalchemy import select

    from app.core.security import get_password_hash
    from app.models.user import Role, UserRole
    user = User(
        organization_id=test_org.id,
        email="orgadmin@apex.org",
        first_name="Org",
        last_name="Admin",
        password_hash=get_password_hash("AdminPass123!"),
        is_active=True,
        is_verified=True,
        is_superuser=False
    )
    db_session.add(user)
    await db_session.flush()

    role_stmt = select(Role).where(Role.code == RoleCode.ADMIN)
    admin_role = (await db_session.execute(role_stmt)).scalars().first()
    if admin_role:
        db_session.add(UserRole(user_id=user.id, role_id=admin_role.id))

    await db_session.commit()
    await db_session.refresh(user)

    return create_access_token(
        subject=user.id,
        organization_id=test_org.id,
        role=RoleCode.ADMIN.value,
        permissions=["election.manage", "voter.manage", "candidate.manage", "result.view", "report.export"]
    )


@pytest_asyncio.fixture
async def volunteer_token(db_session: AsyncSession, test_org: Organization) -> str:
    """Creates a Volunteer user and generates JWT with restricted volunteer role."""
    from sqlalchemy import select

    from app.core.security import get_password_hash
    from app.models.user import Role, UserRole
    user = User(
        organization_id=test_org.id,
        email="fieldvolunteer@apex.org",
        first_name="Field",
        last_name="Volunteer",
        password_hash=get_password_hash("VolunteerPass123!"),
        is_active=True,
        is_verified=True,
        is_superuser=False
    )
    db_session.add(user)
    await db_session.flush()

    role_stmt = select(Role).where(Role.code == RoleCode.VOLUNTEER)
    vol_role = (await db_session.execute(role_stmt)).scalars().first()
    if vol_role:
        db_session.add(UserRole(user_id=user.id, role_id=vol_role.id))

    await db_session.commit()
    await db_session.refresh(user)

    return create_access_token(
        subject=user.id,
        organization_id=test_org.id,
        role=RoleCode.VOLUNTEER.value,
        permissions=["field.data.collect", "field.data.view", "voter.verify"]
    )
