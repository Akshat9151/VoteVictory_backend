import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_broadcast_group_routes_members_drafts_and_logs(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    voters = []
    for index, payload in enumerate([
        {"voter_id_number": "GROUP-WA", "first_name": "WhatsApp", "last_name": "Voter", "phone_number": "+919000000010", "channel": "WhatsApp"},
        {"voter_id_number": "GROUP-SMS", "first_name": "SMS", "last_name": "Voter", "phone_number": "+919000000011", "channel": "SMS Only"},
        {"voter_id_number": "GROUP-NO-CONTACT", "first_name": "No", "last_name": "Contact"},
    ]):
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
