import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_unauthorized_access_denied(client: AsyncClient):
    # Missing token
    resp = await client.get("/api/v1/users/")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_volunteer_privilege_escalation_prevented(client: AsyncClient, volunteer_token: str):
    headers = {"Authorization": f"Bearer {volunteer_token}"}

    # Volunteer attempts to create an organization -> 403
    resp = await client.post("/api/v1/organizations/", json={"name": "Fake Org", "slug": "fake"}, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "PERMISSION_DENIED"

    # Volunteer attempts to create an election -> 403
    elec_resp = await client.post("/api/v1/elections/", json={"title": "Rogue Election", "slug": "rogue"}, headers=headers)
    assert elec_resp.status_code == 403


@pytest.mark.asyncio
async def test_invalid_lifecycle_transition_prevented(client: AsyncClient, superadmin_token: str):
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create Org & Draft Election
    org_resp = await client.post("/api/v1/organizations/", json={"name": "Org 1", "slug": "org-1"}, headers=headers)
    org_id = org_resp.json()["data"]["id"]

    elec_resp = await client.post("/api/v1/elections/", json={"organization_id": org_id, "title": "Test 1", "slug": "test-1"}, headers=headers)
    elec_id = elec_resp.json()["data"]["id"]

    # Attempt illegal jump: DRAFT -> RESULT_PUBLISHED
    jump_resp = await client.post(f"/api/v1/elections/{elec_id}/transition", json={
        "target_status": "RESULT_PUBLISHED"
    }, headers=headers)
    assert jump_resp.status_code == 422
    assert jump_resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
