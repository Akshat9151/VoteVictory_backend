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

@pytest.mark.asyncio
async def test_broadcast_group_single_and_bulk_delete(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Create a voter
    v_res = await client.post("/api/v1/voters/", json={"voter_id_number": "BG-DEL-VOTER", "first_name": "Test", "last_name": "Del", "phone_number": "+919000000099"}, headers=headers)
    assert v_res.status_code == 200
    voter_id = v_res.json()["id"]

    # 2. Create 3 test groups
    g1 = (await client.post("/api/v1/broadcast/groups", json={"name": "Delete Group 1", "voter_ids": [voter_id], "filter_criteria_snapshot": {}}, headers=headers)).json()["id"]
    g2 = (await client.post("/api/v1/broadcast/groups", json={"name": "Delete Group 2", "voter_ids": [voter_id], "filter_criteria_snapshot": {}}, headers=headers)).json()["id"]
    g3 = (await client.post("/api/v1/broadcast/groups", json={"name": "Delete Group 3", "voter_ids": [voter_id], "filter_criteria_snapshot": {}}, headers=headers)).json()["id"]

    # 3. Test single delete
    del_res = await client.delete(f"/api/v1/broadcast/groups/{g1}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Confirm g1 is deleted from list
    list_res = await client.get("/api/v1/broadcast/groups", headers=headers)
    assert list_res.status_code == 200
    remaining_ids = [g["id"] for g in list_res.json()]
    assert g1 not in remaining_ids
    assert g2 in remaining_ids
    assert g3 in remaining_ids

    # 4. Test bulk delete on g2 and g3
    bulk_del_res = await client.request("DELETE", "/api/v1/broadcast/groups/bulk", json={"group_ids": [g2, g3]}, headers=headers)
    assert bulk_del_res.status_code == 200
    assert bulk_del_res.json()["success"] is True
    assert bulk_del_res.json()["data"]["deleted_count"] == 2

    # Confirm all are gone
    list_res2 = await client.get("/api/v1/broadcast/groups", headers=headers)
    remaining_ids2 = [g["id"] for g in list_res2.json()]
    assert g2 not in remaining_ids2
    assert g3 not in remaining_ids2
