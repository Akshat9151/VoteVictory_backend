import pytest
from httpx import AsyncClient
from app.core.config import settings
from app.models.election import ElectionStatus


@pytest.mark.asyncio
async def test_health_endpoints(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == settings.PROJECT_NAME

    resp_live = await client.get("/api/v1/health/live")
    assert resp_live.status_code == 200


@pytest.mark.asyncio
async def test_superadmin_bootstrap_login(client: AsyncClient):
    login_payload = {
        "email": settings.FIRST_SUPER_ADMIN_EMAIL,
        "password": settings.FIRST_SUPER_ADMIN_PASSWORD
    }
    resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["success"] is True
    assert "access_token" in res_data["data"]
    assert res_data["data"]["user"]["is_superuser"] is True


@pytest.mark.asyncio
async def test_election_and_voter_flow(client: AsyncClient):
    # 1. Login as Super Admin
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": settings.FIRST_SUPER_ADMIN_EMAIL,
        "password": settings.FIRST_SUPER_ADMIN_PASSWORD
    })
    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Organization
    org_resp = await client.post("/api/v1/organizations/", json={
        "name": "Rajasthan State Election Board",
        "slug": "rajasthan-election-board",
        "contact_email": "ceo@rajasthan.gov.in"
    }, headers=headers)
    assert org_resp.status_code == 200
    org_id = org_resp.json()["data"]["id"]

    # 3. Create Election
    elec_resp = await client.post("/api/v1/elections/", json={
        "organization_id": org_id,
        "title": "Gram Panchayat Rampur 2026",
        "slug": "rampur-panchayat-2026",
        "description": "Sarpanch and Ward Panch Election",
        "election_type": "LOCAL",
        "timezone": "Asia/Kolkata"
    }, headers=headers)
    assert elec_resp.status_code == 200
    elec_id = elec_resp.json()["data"]["id"]
    assert elec_resp.json()["data"]["status"] == "DRAFT"

    # 4. Create Position
    pos_resp = await client.post("/api/v1/positions/", json={
        "election_id": elec_id,
        "title": "Sarpanch",
        "min_selections": 1,
        "max_selections": 1
    }, headers=headers)
    assert pos_resp.status_code == 200
    pos_id = pos_resp.json()["data"]["id"]

    # 5. Create Candidates
    cand_resp = await client.post("/api/v1/candidates/", json={
        "election_id": elec_id,
        "position_id": pos_id,
        "full_name": "Rameshwar Patel",
        "party_name": "Kisan Vikas Sangh"
    }, headers=headers)
    assert cand_resp.status_code == 200
    cand_id = cand_resp.json()["data"]["id"]

    # Approve Candidate
    app_resp = await client.post(f"/api/v1/candidates/{cand_id}/status", json={
        "status": "APPROVED"
    }, headers=headers)
    assert app_resp.status_code == 200

    # 6. Create Polling Station
    station_resp = await client.post("/api/v1/polling-stations/", json={
        "election_id": elec_id,
        "name": "Govt Senior Secondary School, Rampur",
        "code": "PS-001",
        "address": "Main Road, Rampur Village",
        "capacity": 1500
    }, headers=headers)
    assert station_resp.status_code == 200
    station_id = station_resp.json()["data"]["id"]

    # 7. Create Voter
    voter_resp = await client.post("/api/v1/voters/", json={
        "election_id": elec_id,
        "polling_station_id": station_id,
        "voter_id_number": "RJ2026EPIC001",
        "first_name": "Gopal Lal",
        "last_name": "Gurjar",
        "age": 42,
        "phone_number": "+919829012345"
    }, headers=headers)
    assert voter_resp.status_code == 200
    voter_id = voter_resp.json()["data"]["id"]

    # 8. Checkin Voter
    checkin_resp = await client.post("/api/v1/checkin/", json={
        "voter_id": voter_id,
        "election_id": elec_id,
        "polling_station_id": station_id
    }, headers=headers)
    assert checkin_resp.status_code == 200

    # 9. Transition Election to LIVE
    # DRAFT -> SCHEDULED
    await client.post(f"/api/v1/elections/{elec_id}/transition", json={
        "target_status": "SCHEDULED"
    }, headers=headers)
    # SCHEDULED -> LIVE
    live_resp = await client.post(f"/api/v1/elections/{elec_id}/transition", json={
        "target_status": "LIVE"
    }, headers=headers)
    assert live_resp.status_code == 200
    assert live_resp.json()["data"]["status"] == "LIVE"

    # 10. Authenticate for Electronic Voting
    voter_auth_resp = await client.post("/api/v1/voting/auth-ballot", json={
        "voter_id_number": "RJ2026EPIC001",
        "election_id": elec_id
    })
    assert voter_auth_resp.status_code == 200
    session_token = voter_auth_resp.json()["data"]["session_token"]
    assert session_token is not None

    # 11. Cast Anonymous Vote
    cast_resp = await client.post(f"/api/v1/voting/cast?voter_id={voter_id}", json={
        "session_token": session_token,
        "election_id": elec_id,
        "selections": [
            {
                "position_id": pos_id,
                "candidate_ids": [cand_id]
            }
        ]
    })
    assert cast_resp.status_code == 200
    receipt = cast_resp.json()["data"]
    assert receipt["success"] is True
    assert "ballot_serial_hash" in receipt

    # 12. Attempt Double Voting -> MUST BE REJECTED
    double_auth_resp = await client.post("/api/v1/voting/auth-ballot", json={
        "voter_id_number": "RJ2026EPIC001",
        "election_id": elec_id
    })
    assert double_auth_resp.status_code == 409 # DOUBLE_VOTING_PREVENTED

    # 13. Tally & Publish Results
    tally_resp = await client.post(f"/api/v1/results/election/{elec_id}/tally", headers=headers)
    assert tally_resp.status_code == 200
    summary = tally_resp.json()["data"]
    assert summary["total_votes_cast"] == 1
    assert summary["turnout_percentage"] == 100.0

    pub_resp = await client.post("/api/v1/results/publish", json={
        "election_id": elec_id,
        "notes": "Certified by Returning Officer"
    }, headers=headers)
    assert pub_resp.status_code == 200
    assert pub_resp.json()["data"]["status"] == "PUBLISHED"
