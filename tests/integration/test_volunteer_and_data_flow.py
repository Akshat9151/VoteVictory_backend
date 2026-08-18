import pytest
from httpx import AsyncClient
from app.core.config import settings


@pytest.mark.asyncio
async def test_volunteer_and_data_collection_lifecycle(client: AsyncClient):
    # 1. Login as SuperAdmin to get token
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.FIRST_SUPER_ADMIN_EMAIL,
            "password": settings.FIRST_SUPER_ADMIN_PASSWORD,
        },
    )
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Organization & Election
    org_res = await client.post(
        "/api/v1/organizations/",
        headers=headers,
        json={
            "name": "State Operations Board",
            "slug": "state-ops-board",
            "contact_email": "ops@stateops.org",
        },
    )
    assert org_res.status_code == 200
    org_id = org_res.json()["data"]["id"]

    elec_res = await client.post(
        "/api/v1/elections/",
        headers=headers,
        json={
            "organization_id": org_id,
            "title": "State General Election 2026",
            "slug": "state-gen-election-2026",
            "election_type": "GENERAL",
            "timezone": "UTC",
        },
    )
    assert elec_res.status_code == 200
    election_id = elec_res.json()["data"]["id"]

    # 3. Create Constituency & Booth
    constituency_res = await client.post(
        "/api/v1/constituencies/",
        headers=headers,
        json={"election_id": election_id, "name": "East Central", "code": "EC-01"},
    )
    assert constituency_res.status_code == 200
    const_id = constituency_res.json()["data"]["id"]

    booth_res = await client.post(
        "/api/v1/geography/booths",
        headers=headers,
        json={
            "constituency_id": const_id,
            "booth_number": "B-101",
            "name": "East City Hall Booth",
            "location_address": "100 Main St",
            "target": 500,
        },
    )
    assert booth_res.status_code == 200
    booth_id = booth_res.json()["data"]["id"]

    # 4. Onboard a Volunteer
    vol_res = await client.post(
        "/api/v1/volunteers",
        headers=headers,
        json={
            "first_name": "Field",
            "last_name": "Worker",
            "email": "field.worker@example.com",
            "password": "WorkerSecurePassword123!",
            "phone": "+12025550199",
            "election_id": election_id,
            "constituency_id": const_id,
            "booth_id": booth_id,
            "daily_target": 100,
            "monthly_target": 2500,
        },
    )
    assert vol_res.status_code == 200
    vol_profile_id = vol_res.json()["data"]["id"]

    # 5. Verify volunteer leaderboard and performance
    leaderboard_res = await client.get("/api/v1/volunteers/leaderboard", headers=headers)
    assert leaderboard_res.status_code == 200
    assert len(leaderboard_res.json()["data"]) >= 1

    perf_res = await client.get(f"/api/v1/volunteers/{vol_profile_id}/performance", headers=headers)
    assert perf_res.status_code == 200
    assert perf_res.json()["data"]["monthly_target"] == 2500

    # 6. Submit Field Data Record
    sub_res = await client.post(
        "/api/v1/data/submit",
        headers=headers,
        json={
            "citizen_name": "Robert Citizen",
            "mobile": "+12025550177",
            "email": "robert.c@example.com",
            "voter_card_number": "EPIC-998877",
            "booth_no": "B-101",
            "constituency_id": const_id,
            "booth_id": booth_id,
            "election_id": election_id,
        },
    )
    assert sub_res.status_code == 200
    sub_data = sub_res.json()["data"]
    assert sub_data["citizen_name"] == "Robert Citizen"
    assert sub_data["quality_score"] == 100.0
    submission_id = sub_data["id"]

    # 7. Submit Duplicate Record (Same mobile & voter card)
    dup_sub_res = await client.post(
        "/api/v1/data/submit",
        headers=headers,
        json={
            "citizen_name": "Robert Citizen Duplicate",
            "mobile": "+12025550177",
            "voter_card_number": "EPIC-998877",
            "booth_no": "B-101",
            "election_id": election_id,
        },
    )
    assert dup_sub_res.status_code == 200
    dup_data = dup_sub_res.json()["data"]
    assert dup_data["status"] == "DUPLICATE"
    assert dup_data["is_flagged_duplicate"] is True

    # 8. Check Duplicates list & resolve
    dups_list_res = await client.get("/api/v1/data/duplicates", headers=headers)
    assert dups_list_res.status_code == 200
    assert dups_list_res.json()["data"]["total"] >= 1
    dup_record_id = dups_list_res.json()["data"]["items"][0]["id"]

    resolve_res = await client.post(
        "/api/v1/data/duplicates/resolve",
        headers=headers,
        json={
            "duplicate_id": dup_record_id,
            "action": "MERGED",
            "primary_record_id": submission_id,
            "resolution_notes": "Merged identical citizen records",
        },
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["data"]["resolution_status"] == "MERGED"

    # 9. Admin Review Center - Approve Primary Record
    review_res = await client.post(
        f"/api/v1/data/submissions/{submission_id}/review",
        headers=headers,
        json={"action": "APPROVE", "remarks": "Verified by field supervisor"},
    )
    assert review_res.status_code == 200
    assert review_res.json()["data"]["status"] == "APPROVED"

    # 10. Data Quality Stats
    quality_stats_res = await client.get("/api/v1/data/quality/stats", headers=headers)
    assert quality_stats_res.status_code == 200
    assert quality_stats_res.json()["data"]["total_records"] >= 2
    assert quality_stats_res.json()["data"]["approved_records"] >= 1

    # 11. Templates & Variable Preview
    tmpl_res = await client.post(
        "/api/v1/templates",
        headers=headers,
        json={
            "name": "Polling Alert",
            "code": "POLL_ALERT_01",
            "channel": "SMS",
            "content_template": "Hello {{name}}, your voting booth is {{booth}} on {{date}}.",
        },
    )
    assert tmpl_res.status_code == 200
    tmpl_id = tmpl_res.json()["data"]["id"]

    preview_res = await client.post(
        "/api/v1/templates/preview",
        headers=headers,
        json={
            "template_id": tmpl_id,
            "sample_data": {"name": "Alex", "booth": "B-101", "date": "2026-11-04"},
        },
    )
    assert preview_res.status_code == 200
    assert "Hello Alex, your voting booth is B-101 on 2026-11-04." in preview_res.json()["data"]["rendered_preview"]

    # 12. Banners
    banner_res = await client.post(
        "/api/v1/banners",
        headers=headers,
        json={
            "title": "Vote Early Campaign",
            "image_url": "https://images.example.com/vote-banner.png",
            "cta_text": "Find Your Booth",
            "cta_link": "https://votingplatform.org/booths",
            "election_id": election_id,
            "status": "PUBLISHED",
        },
    )
    assert banner_res.status_code == 200
    assert banner_res.json()["data"]["status"] == "PUBLISHED"

    # 13. Reports CSV Export
    report_csv_res = await client.get("/api/v1/reports/volunteers/export/csv", headers=headers)
    assert report_csv_res.status_code == 200
    assert "Volunteer Name" in report_csv_res.text

    # 14. Operational Dashboard & Analytics
    dash_res = await client.get("/api/v1/dashboard/admin", headers=headers)
    assert dash_res.status_code == 200
    assert dash_res.json()["data"]["total_volunteers"] >= 1

    charts_res = await client.get("/api/v1/analytics/charts", headers=headers)
    assert charts_res.status_code == 200
    assert len(charts_res.json()["data"]["daily_collection_trend"]) == 7
