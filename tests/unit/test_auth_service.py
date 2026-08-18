import pytest
from app.core.exceptions import AuthenticationException
from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_auth_login_success(db_session, test_org):
    service = AuthService(db_session)
    # Seeded superadmin login
    req = LoginRequest(
        phone="+91 98290 14285",
        password="SuperSecureAdminPassword123!",
        role="superadmin"
    )
    res = await service.login(req)
    assert res.token is not None
    assert res.access_token is not None
    assert res.refresh_token is not None
    assert res.user.role == "superadmin"
    assert res.user.name == "Rameshwar Patel (Owner)"


@pytest.mark.asyncio
async def test_auth_login_invalid_password(db_session):
    service = AuthService(db_session)
    req = LoginRequest(
        phone="+91 98290 14285",
        password="WrongPassword123!",
        role="superadmin"
    )
    with pytest.raises(AuthenticationException):
        await service.login(req)


@pytest.mark.asyncio
async def test_auth_token_refresh(db_session):
    service = AuthService(db_session)
    login_req = LoginRequest(
        phone="+91 98290 14285",
        password="SuperSecureAdminPassword123!",
        role="superadmin"
    )
    login_res = await service.login(login_req)
    refresh_token = login_res.refresh_token

    # Perform refresh
    refresh_res = await service.refresh_tokens(refresh_token)
    assert refresh_res.token is not None
    assert refresh_res.refresh_token is not None
    assert refresh_res.refresh_token != refresh_token  # Token rotation


@pytest.mark.asyncio
async def test_auth_demo_fast_login(db_session):
    service = AuthService(db_session)
    # Fast login without password creates/fetches role profile
    req = LoginRequest(
        phone="+91 99999 88888",
        role="volunteer"
    )
    res = await service.login(req)
    assert res.user.role == "volunteer"
    assert res.token is not None
