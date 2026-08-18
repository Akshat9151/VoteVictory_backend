import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_volunteer_forbidden_from_adding_candidate(client: AsyncClient, volunteer_token: str):
    headers = {"Authorization": f"Bearer {volunteer_token}"}
    candidate_payload = {
        "name": "Unauthorized Candidate",
        "post": "Sarpanch",
        "postType": "sarpanch",
        "constituency": "Ward 01",
        "symbol": "🚲",
        "symbolName": "Bicycle",
        "votersCount": 100,
        "volunteersCount": 2
    }
    response = await client.post("/api/v1/candidates", json=candidate_payload, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_allowed_to_add_candidate(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    candidate_payload = {
        "name": "Authorized Candidate",
        "post": "Sarpanch",
        "postType": "sarpanch",
        "constituency": "Ward 01",
        "symbol": "🚲",
        "symbolName": "Bicycle",
        "votersCount": 100,
        "volunteersCount": 2
    }
    response = await client.post("/api/v1/candidates", json=candidate_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Authorized Candidate"


@pytest.mark.asyncio
async def test_volunteer_forbidden_from_adding_expense(client: AsyncClient, volunteer_token: str):
    headers = {"Authorization": f"Bearer {volunteer_token}"}
    expense_payload = {
        "category": "Unauthorized Expense",
        "amount": 2000.0,
        "note": "Volunteer attempt",
        "mode": "Cash Voucher",
        "user": "Volunteer"
    }
    response = await client.post("/api/v1/expenses", json=expense_payload, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient):
    response = await client.post("/api/v1/expenses", json={"category": "Test", "amount": 100.0})
    assert response.status_code == 401
