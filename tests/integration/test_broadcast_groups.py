import pytest
import time
from httpx import AsyncClient
from sqlalchemy import func, select

from app.models.broadcast import BroadcastGroupMember, BroadcastLog


@pytest.mark.asyncio
async def test_broadcast_group_routes_members_drafts_and_logs(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    voters = []
    unique_ts = int(time.time() * 1000) % 1000000
    for index in range(3):
        if index == 0:
            payload = {"voter_id_number": f"GROUP-WA-{unique_ts}-{index}", "first_name": "WhatsApp", "last_name": "Voter", "phone_number": f"+91900000{unique_ts:04d}{index}", "channel": "WhatsApp"}
        elif index == 1:
            payload = {"voter_id_number": f"GROUP-SMS-{unique_ts}-{index}", "first_name": "SMS", "last_name": "Voter", "phone_number": f"+91900001{unique_ts:04d}{index}", "channel": "SMS Only"}
        else:
            payload = {"voter_id_number": f"GROUP-NO-CONTACT-{unique_ts}-{index}", "first_name": "No", "last_name": "Contact"}
        response = await client.post("/api/v1/voters/", json=payload, headers=headers)
        assert response.status_code == 200, response.text
        voters.append(response.json()["id"])

    group_response = await client.post(
        "/api/v1/broadcast/groups",
        json={"voter_ids": voters, "filter_criteria_snapshot": {"label": "Ward 1 Women"}},
        headers=headers,
    )
    assert group_response.status_code == 201, group_response.text
    group = group_response.json()
    assert group["recipient_count"] == 2
    assert group["whatsapp_count"] == 1
    assert group["sms_count"] == 1
    assert group["excluded_no_contact"] == 1

    draft_response = await client.patch(
        f"/api/v1/broadcast/groups/{group['id']}/draft",
        json={"message_text": "नमस्ते {{name}}, वार्ड {{ward}} में आपका स्वागत है।"},
        headers=headers,
    )
    assert draft_response.status_code == 200, draft_response.text
    assert draft_response.json()["status"] == "READY"

    send_response = await client.post(f"/api/v1/broadcast/{group['id']}/send", headers=headers)
    assert send_response.status_code == 200, send_response.text
    result = send_response.json()
    assert result["total"] == 2
    assert result["whatsapp_sent"] == 1
    assert result["sms_sent"] == 1
    assert result["failed"] == 0

    logs_response = await client.get(f"/api/v1/broadcast/{group['id']}/logs", headers=headers)
    assert logs_response.status_code == 200
    logs = logs_response.json()
    assert {log["channel_used"] for log in logs} == {"whatsapp", "sms"}
    assert all(log["status"] == "success" for log in logs)


@pytest.mark.asyncio
async def test_broadcast_group_delete_and_bulk_delete_cascade(
    client: AsyncClient,
    db_session,
    admin_token: str,
    volunteer_token: str,
):
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    volunteer_headers = {"Authorization": f"Bearer {volunteer_token}"}

    unique_suffix = int(time.time() * 1000) % 100000
    voter_response = await client.post(
        "/api/v1/voters/",
        json={
            "voter_id_number": f"DELETE-TEST-{unique_suffix}",
            "first_name": "Delete",
            "last_name": "Test",
            "phone_number": f"+919000{unique_suffix:05d}",
            "channel": "WhatsApp",
        },
        headers=admin_headers,
    )
    assert voter_response.status_code == 200, voter_response.text
    voter_id = voter_response.json()["id"]

    group_ids = []
    for index in range(3):
        response = await client.post(
            "/api/v1/broadcast/groups",
            json={"voter_ids": [voter_id], "filter_criteria_snapshot": {"test": index}},
            headers=admin_headers,
        )
        assert response.status_code == 201, response.text
        group_ids.append(response.json()["id"])

    draft_response = await client.patch(
        f"/api/v1/broadcast/groups/{group_ids[0]}/draft",
        json={"message_text": "Test delete message"},
        headers=admin_headers,
    )
    assert draft_response.status_code == 200, draft_response.text

    send_response = await client.post(f"/api/v1/broadcast/{group_ids[0]}/send", headers=admin_headers)
    assert send_response.status_code == 200, send_response.text

    denied_response = await client.delete(f"/api/v1/broadcast/groups/{group_ids[1]}", headers=volunteer_headers)
    assert denied_response.status_code == 403

    delete_response = await client.delete(f"/api/v1/broadcast/groups/{group_ids[0]}", headers=admin_headers)
    assert delete_response.status_code == 200, delete_response.text
    remaining_groups = await client.get("/api/v1/broadcast/groups", headers=admin_headers)
    assert group_ids[0] not in {group["id"] for group in remaining_groups.json()}

    member_count = await db_session.scalar(
        select(func.count()).select_from(BroadcastGroupMember).where(BroadcastGroupMember.group_id == group_ids[0])
    )
    log_count = await db_session.scalar(
        select(func.count()).select_from(BroadcastLog).where(BroadcastLog.group_id == group_ids[0])
    )
    assert member_count == 0
    assert log_count == 0

    bulk_response = await client.request(
        "DELETE",
        "/api/v1/broadcast/groups/bulk",
        json={"group_ids": group_ids[1:]},
        headers=admin_headers,
    )
    assert bulk_response.status_code == 200, bulk_response.text
    assert bulk_response.json()["data"]["deleted_count"] == 2

    final_groups = await client.get("/api/v1/broadcast/groups", headers=admin_headers)
    assert {group["id"] for group in final_groups.json()} == set()
