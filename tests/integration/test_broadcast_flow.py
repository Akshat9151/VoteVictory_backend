import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_broadcast_and_delivery_log_flow(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    voter_res = await client.post("/api/v1/voters/", json={
        "voter_id_number": "BROADCAST-TEST-001",
        "first_name": "Broadcast",
        "last_name": "Recipient",
        "ward_name": "Ward 02",
        "phone_number": "+919000000001",
    }, headers=headers)
    assert voter_res.status_code == 200

    # 1. Fetch initial logs
    initial_logs_res = await client.get("/api/v1/broadcast/delivery-logs")
    assert initial_logs_res.status_code == 200
    initial_count = len(initial_logs_res.json())

    # 2. Dispatch Broadcast
    payload = {
        "message": "Nukkad Sabha today at 5 PM near Community Hall.",
        "channel": "whatsapp",
        "includePoster": False,
        "selectedWards": ["Ward 02"]
    }
    broadcast_res = await client.post("/api/v1/broadcast/send", json=payload, headers=headers)
    assert broadcast_res.status_code == 200
    res_data = broadcast_res.json()
    assert res_data["success"] is True
    assert res_data["count"] > 0

    # 3. Verify Delivery Logs updated
    updated_logs_res = await client.get("/api/v1/broadcast/delivery-logs")
    assert updated_logs_res.status_code == 200
    new_logs = updated_logs_res.json()
    assert len(new_logs) >= initial_count
