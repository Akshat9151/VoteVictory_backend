import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_complaint_crud_and_dashboard_counts(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    create_voter = await client.post("/api/v1/voters/", json={"voter_id_number": "DASH-VOTER-1", "first_name": "Dashboard", "last_name": "Voter", "phone_number": "+919111111111"}, headers=headers)
    assert create_voter.status_code == 200

    created = await client.post("/api/v1/complaints/election/dashboard-election", json={
        "title": "Street light issue",
        "reported_by_name": "Meena Devi",
        "ward_name": "Ward 7 - North",
        "category": "Street Lighting",
        "description": "Two lights are not working.",
    }, headers=headers)
    assert created.status_code == 200, created.text
    complaint = created.json()["data"]
    complaint_id = complaint["id"]
    assert complaint["election_id"] == "dashboard-election"

    updated = await client.put(f"/api/v1/complaints/{complaint_id}", json={"ward_name": "Ward 8 - South", "category": "Electricity", "description": "Updated issue"}, headers=headers)
    assert updated.status_code == 200, updated.text
    assert updated.json()["ward_name"] == "Ward 8 - South"
    assert updated.json()["category"] == "Electricity"

    listed = await client.get("/api/v1/complaints/election/dashboard-election", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == complaint_id for item in listed.json()["data"]["items"])

    deleted = await client.delete(f"/api/v1/complaints/{complaint_id}", headers=headers)
    assert deleted.status_code == 200
    listed_after_delete = await client.get("/api/v1/complaints/election/dashboard-election", headers=headers)
    assert all(item["id"] != complaint_id for item in listed_after_delete.json()["data"]["items"])

    dashboard = await client.get("/api/v1/dashboard/admin", headers=headers)
    assert dashboard.status_code == 200
    dashboard_data = dashboard.json()["data"]
    assert dashboard_data["total_voters"] >= 1
    assert "total_candidates" not in dashboard_data
