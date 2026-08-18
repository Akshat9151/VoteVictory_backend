import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["online", "healthy"]
    assert "service" in data


@pytest.mark.asyncio
async def test_candidates_flow(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Get Candidates
    get_res = await client.get("/api/v1/candidates")
    assert get_res.status_code == 200
    candidates = get_res.json()
    assert isinstance(candidates, list)

    # 2. Add Candidate
    new_cand = {
        "name": "Suresh Choudhary",
        "hindiName": "सुरेश चौधरी",
        "post": "Panch (Ward)",
        "postType": "panch",
        "constituency": "Ward 05",
        "symbol": "🏏",
        "symbolName": "Cricket Bat",
        "photo": "",
        "slogan": "विकास ही संकल्प!",
        "votersCount": 500,
        "volunteersCount": 4,
        "manifesto": "Streetlights and water"
    }
    post_res = await client.post("/api/v1/candidates", json=new_cand, headers=headers)
    assert post_res.status_code == 200
    assert post_res.json()["name"] == "Suresh Choudhary"


@pytest.mark.asyncio
async def test_team_and_volunteers_flow(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Get Team
    team_res = await client.get("/api/v1/team")
    assert team_res.status_code == 200
    assert isinstance(team_res.json(), list)

    # Add Team Member
    new_member = {
        "name": "Om Prakash",
        "role": "Volunteer",
        "roleTitle": "Booth Incharge",
        "ward": "Ward 05",
        "phone": "+91 98765 43210",
        "status": "Active"
    }
    post_res = await client.post("/api/v1/team", json=new_member, headers=headers)
    assert post_res.status_code == 200
    assert post_res.json()["name"] == "Om Prakash"

    # Get Volunteers
    vol_res = await client.get("/api/v1/volunteers")
    assert vol_res.status_code == 200
    assert isinstance(vol_res.json(), list)


@pytest.mark.asyncio
async def test_voters_flow(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Get Voters
    get_res = await client.get("/api/v1/voters")
    assert get_res.status_code == 200
    assert isinstance(get_res.json(), list)

    # 2. Add Single Voter
    single_voter = {
        "name": "Manish Verma",
        "age": 29,
        "gender": "Male",
        "ward": "Ward 03",
        "mobile": "+91 97777 66666",
        "channel": "WhatsApp",
        "consent": "Verified",
        "source": "Survey"
    }
    post_res = await client.post("/api/v1/voters", json=single_voter, headers=headers)
    assert post_res.status_code == 200
    assert post_res.json()["name"] == "Manish Verma"

    # 3. Batch Add
    batch = [
        {"name": "Batch Voter 1", "age": 20, "gender": "Female", "ward": "Ward 01", "mobile": "+91 91234 56789"},
        {"name": "Batch Voter 2", "age": 22, "gender": "Male", "ward": "Ward 02", "mobile": "+91 91234 56780"}
    ]
    batch_res = await client.post("/api/v1/voters/batch", json=batch, headers=headers)
    assert batch_res.status_code == 200
    assert len(batch_res.json()) == 2

    # 4. Audience Split
    split_res = await client.get("/api/v1/voters/audience-split")
    assert split_res.status_code == 200
    split_data = split_res.json()
    assert "whatsapp" in split_data
    assert "sms" in split_data
    assert "total" in split_data


@pytest.mark.asyncio
async def test_complaints_flow(client: AsyncClient, admin_token: str, volunteer_token: str):
    vol_headers = {"Authorization": f"Bearer {volunteer_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Get Complaints
    get_res = await client.get("/api/v1/complaints")
    assert get_res.status_code == 200
    assert isinstance(get_res.json(), list)

    # 2. File Complaint (Volunteer can file)
    new_comp = {
        "name": "Ramu Kaka",
        "ward": "Ward 02",
        "category": "Water Supply",
        "desc": "Pipe burst near temple",
        "status": "Open"
    }
    post_res = await client.post("/api/v1/complaints", json=new_comp, headers=vol_headers)
    assert post_res.status_code == 200
    created_id = post_res.json()["id"]

    # 3. Patch Status (Admin updates)
    patch_res = await client.patch(
        f"/api/v1/complaints/{created_id}/status",
        json={"status": "In Progress"},
        headers=admin_headers
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "In Progress"


@pytest.mark.asyncio
async def test_expenses_flow(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Get Expenses
    get_res = await client.get("/api/v1/expenses")
    assert get_res.status_code == 200
    assert isinstance(get_res.json(), list)

    # 2. Add Expense
    new_exp = {
        "category": "Tea & Refreshments",
        "amount": 3500.0,
        "note": "Worker snacks",
        "mode": "UPI / Online",
        "user": "Rajesh Kumar"
    }
    post_res = await client.post("/api/v1/expenses", json=new_exp, headers=headers)
    assert post_res.status_code == 200
    assert post_res.json()["amount"] == 3500.0

    # 3. Get Budget Summary
    summary_res = await client.get("/api/v1/expenses/budget-summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["budgetLimit"] > 0
    assert summary["totalSpent"] >= 0

@pytest.mark.asyncio
async def test_booths_and_canvassing_flow(client: AsyncClient, volunteer_token: str):
    headers = {"Authorization": f"Bearer {volunteer_token}"}

    # 1. Get Booths
    booths_res = await client.get("/api/v1/booths")
    assert booths_res.status_code == 200
    assert isinstance(booths_res.json(), list)

    # 2. Add and Get Volunteer Voter
    new_vv = {
        "name": "Kailash Gurjar",
        "age": 42,
        "mobile": "+91 98888 77777",
        "house": "House 102",
        "status": "Pending",
        "slipHanded": False
    }
    add_vv_res = await client.post("/api/v1/volunteer-voters", json=new_vv, headers=headers)
    assert add_vv_res.status_code == 200
    target_id = add_vv_res.json()["id"]

    # 3. Patch Canvassing Status
    patch_res = await client.patch(
        f"/api/v1/volunteer-voters/{target_id}/status",
        json={"status": "Visited", "slipHanded": True},
        headers=headers
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "Visited"
    assert patch_res.json()["slipHanded"] is True


@pytest.mark.asyncio
async def test_broadcast_and_analytics_flow(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Get Delivery Logs
    logs_res = await client.get("/api/v1/broadcast/delivery-logs")
    assert logs_res.status_code == 200
    assert isinstance(logs_res.json(), list)

    # 2. Send Broadcast
    broadcast_payload = {
        "message": "Vote for Rameshwar Patel on Tractor symbol!",
        "channel": "all",
        "includePoster": True,
        "selectedWards": ["Ward 04", "Ward 02"]
    }
    send_res = await client.post("/api/v1/broadcast/send", json=broadcast_payload, headers=headers)
    assert send_res.status_code == 200
    assert send_res.json()["success"] is True

    # 3. Get Analytics
    analytics_res = await client.get("/api/v1/analytics")
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert "wardCoverage" in analytics
    assert "channelDelivery" in analytics
    assert "materialPrints" in analytics
    assert "volunteerProductivity" in analytics


@pytest.mark.asyncio
async def test_audit_logs_flow(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = await client.get("/api/v1/audit-logs", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)
