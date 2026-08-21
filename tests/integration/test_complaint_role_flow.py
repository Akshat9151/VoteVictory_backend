import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_complaint_role_permissions_and_ownership(client: AsyncClient, db_session, admin_token: str, volunteer_token: str, superadmin_token: str):
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    volunteer_headers = {"Authorization": f"Bearer {volunteer_token}"}
    super_headers = {"Authorization": f"Bearer {superadmin_token}"}
    payload = {"title": "Street light report", "reported_by_name": "Public Citizen", "reported_by_phone": "+919999999999", "ward_name": "Ward 9", "category": "Street Lighting", "description": "Light is broken."}

    admin_create = await client.post("/api/v1/complaints/election/role-test", json=payload, headers=admin_headers)
    volunteer_create = await client.post("/api/v1/complaints/election/role-test", json=payload, headers=volunteer_headers)
    assert admin_create.status_code == 200
    assert volunteer_create.status_code == 200
    admin_id = admin_create.json()["data"]["id"]
    volunteer_id = volunteer_create.json()["data"]["id"]

    assert (await client.post("/api/v1/complaints", json=payload, headers=super_headers)).status_code == 403
    assert (await client.put(f"/api/v1/complaints/{admin_id}", json={"ward_name": "Ward 10"}, headers=super_headers)).status_code == 403
    assert (await client.delete(f"/api/v1/complaints/{admin_id}", headers=super_headers)).status_code == 403
    assert (await client.put(f"/api/v1/complaints/{admin_id}/status", json={"status": "In Progress"}, headers=admin_headers)).status_code == 403

    updated = await client.put(f"/api/v1/complaints/{admin_id}", json={"ward_name": "Ward 10"}, headers=admin_headers)
    assert updated.status_code == 200
    status = await client.put(f"/api/v1/complaints/{admin_id}/status", json={"status": "Resolved"}, headers=super_headers)
    assert status.status_code == 200
    assert status.json()["status"] == "Resolved"

    admin_list = await client.get("/api/v1/complaints/election/role-test", headers=admin_headers)
    volunteer_list = await client.get("/api/v1/complaints/election/role-test", headers=volunteer_headers)
    super_list = await client.get("/api/v1/complaints/election/role-test", headers=super_headers)
    assert [item["id"] for item in admin_list.json()["data"]["items"]] == [admin_id]
    assert [item["id"] for item in volunteer_list.json()["data"]["items"]] == [volunteer_id]
    assert {item["id"] for item in super_list.json()["data"]["items"]} >= {admin_id, volunteer_id}

    assert (await client.delete(f"/api/v1/complaints/{admin_id}", headers=admin_headers)).status_code == 200
    assert (await client.delete(f"/api/v1/complaints/{volunteer_id}", headers=volunteer_headers)).status_code == 200
