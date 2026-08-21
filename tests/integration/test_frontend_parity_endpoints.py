import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_design_templates_crud(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create template
    new_template = {
        "title": "Custom Test Banner",
        "category": "Banner",
        "canvas_json": '{"elements":[{"id":"1","type":"text","content":"Vote For Progress"}]}',
        "tags": ["banner", "election", "test"],
    }
    create_res = await client.post("/api/v1/design-templates", json=new_template, headers=headers)
    assert create_res.status_code == 201
    created_envelope = create_res.json()
    created_data = created_envelope["data"] if "data" in created_envelope else created_envelope
    assert created_data["title"] == "Custom Test Banner"
    template_id = created_data["id"]

    # 2. List templates
    res = await client.get("/api/v1/design-templates", headers=headers)
    assert res.status_code == 200
    res_data = res.json()
    items = res_data["data"] if "data" in res_data else res_data
    assert isinstance(items, list)
    assert any(t["id"] == template_id for t in items)

    # 3. Get by ID
    get_res = await client.get(f"/api/v1/design-templates/{template_id}", headers=headers)
    assert get_res.status_code == 200
    get_data = get_res.json()
    get_item = get_data["data"] if "data" in get_data else get_data
    assert get_item["title"] == "Custom Test Banner"

    # 4. Update
    patch_res = await client.patch(
        f"/api/v1/design-templates/{template_id}",
        json={"title": "Updated Test Banner"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    patch_data = patch_res.json()
    patch_item = patch_data["data"] if "data" in patch_data else patch_data
    assert patch_item["title"] == "Updated Test Banner"

    # 5. Delete
    del_res = await client.delete(f"/api/v1/design-templates/{template_id}", headers=headers)
    assert del_res.status_code in [200, 204]


@pytest.mark.asyncio
async def test_field_activities_and_attendance(client: AsyncClient, volunteer_token: str, admin_token: str):
    vol_headers = {"Authorization": f"Bearer {volunteer_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Submit field activity
    activity_payload = {
        "volunteer_name": "Ramesh Kumar",
        "ward": "Ward 02",
        "booth_no": "Booth 02",
        "activity_type": "Panna Pramukh Meeting",
        "location": "Community Center, Rampur",
        "description": "Met 25 panna heads and distributed campaign badges",
        "voters_contacted": 25,
        "slips_distributed": 25,
    }
    submit_res = await client.post("/api/v1/field-activities/submit", json=activity_payload, headers=vol_headers)
    assert submit_res.status_code == 201
    act_data = submit_res.json()
    assert act_data["voters_contacted"] == 25
    act_id = act_data["id"]

    # 2. Update status (admin verify)
    status_res = await client.put(f"/api/v1/field-activities/{act_id}/status", json={"status": "VERIFIED"}, headers=admin_headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] in ["Verified", "VERIFIED"]

    # 3. List activities
    list_res = await client.get("/api/v1/field-activities?ward=Ward 02", headers=vol_headers)
    assert list_res.status_code == 200
    assert any(a["id"] == act_id for a in list_res.json())

    # 4. Check-in
    checkin_res = await client.post(
        "/api/v1/attendance/check-in",
        json={"volunteer_name": "Ramesh Kumar", "ward": "Ward 02", "location": "Booth 02 Gate"},
        headers=vol_headers,
    )
    assert checkin_res.status_code == 201
    assert checkin_res.json()["status"] == "Present"


@pytest.mark.asyncio
async def test_tasks_lifecycle(client: AsyncClient, admin_token: str, volunteer_token: str):
    from app.core.security import decode_access_token
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    vol_payload = decode_access_token(volunteer_token)
    assignee_id = vol_payload["sub"]

    # 1. Create task
    task_payload = {
        "title": "Distribute Voter Slips in Ward 03",
        "description": "Ensure 100% slip distribution before Friday",
        "priority": "high",
        "deadline": "2026-08-25",
        "assigned_to_id": assignee_id,
        "ward_or_booth": "Ward 03",
        "category": "Voter Slip Distribution",
    }
    task_res = await client.post("/api/v1/tasks/create", json=task_payload, headers=admin_headers)
    assert task_res.status_code == 201
    task_data = task_res.json()
    task_id = task_data["id"]
    assert task_data["title"] == "Distribute Voter Slips in Ward 03"

    # 2. Update task status to In Progress
    put_status_res = await client.put(f"/api/v1/tasks/{task_id}/status", json={"status": "in_progress"}, headers=admin_headers)
    assert put_status_res.status_code == 200
    assert put_status_res.json()["status"] in ["in_progress", "IN_PROGRESS"]

    # 3. Update task details
    put_task_res = await client.put(f"/api/v1/tasks/{task_id}", json={"title": "Updated Task Title"}, headers=admin_headers)
    assert put_task_res.status_code == 200
    assert put_task_res.json()["title"] == "Updated Task Title"

    # 4. Delete task
    del_res = await client.delete(f"/api/v1/tasks/{task_id}", headers=admin_headers)
    assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_complaints_and_expenses_election_endpoints(client: AsyncClient, admin_token: str, superadmin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    super_headers = {"Authorization": f"Bearer {superadmin_token}"}
    election_id = "test-elec-parity-1"

    # 1. Add election complaint
    complaint_payload = {
        "title": "Low Water Pressure in Street 4",
        "reported_by_name": "Anita Verma",
        "ward_name": "Ward 04",
        "category": "Water Supply",
        "description": "Water supply pressure is low in the morning hours.",
    }
    comp_res = await client.post(f"/api/v1/complaints/election/{election_id}", json=complaint_payload, headers=headers)
    assert comp_res.status_code == 200
    comp_json = comp_res.json()
    assert comp_json["success"] is True
    assert comp_json["data"]["category"] == "Water Supply"
    comp_id = comp_json["data"]["id"]

    # 2. Update complaint status (requires Super Admin)
    up_comp_res = await client.put(f"/api/v1/complaints/{comp_id}/status", json={"status": "In Progress"}, headers=super_headers)
    assert up_comp_res.status_code == 200
    assert up_comp_res.json()["status"] == "In Progress"

    # 3. Add election expense
    expense_payload = {
        "title": "Stage Fabrication & Sound",
        "category": "PUBLIC_MEETING",
        "amount": 8500.0,
        "mode": "UPI / Online",
        "note": "Public rally sound setup",
    }
    exp_res = await client.post(f"/api/v1/expenses/election/{election_id}", json=expense_payload, headers=headers)
    assert exp_res.status_code == 200
    exp_json = exp_res.json()
    assert exp_json["success"] is True
    assert exp_json["data"]["amount"] == 8500.0

    # 4. Get election budget summary
    summary_res = await client.get(f"/api/v1/expenses/election/{election_id}/summary", headers=headers)
    assert summary_res.status_code == 200
    summary_data = summary_res.json()["data"]
    assert summary_data["budget_limit"] == 150000.0
    assert summary_data["total_spent"] >= 8500.0


@pytest.mark.asyncio
async def test_analytics_and_broadcast_split(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    election_id = "test-elec-turnout-1"

    # 1. Turnout analytics
    turnout_res = await client.get(f"/api/v1/analytics/election/{election_id}/turnout", headers=headers)
    assert turnout_res.status_code == 200
    turnout_json = turnout_res.json()
    assert turnout_json["success"] is True
    assert "wardCoverage" in turnout_json["data"]

    # 2. Audience split
    split_res = await client.get("/api/v1/broadcast/audience-split", headers=headers)
    assert split_res.status_code == 200
    split_data = split_res.json()
    assert "whatsapp_count" in split_data or "whatsapp" in split_data or "total_voters" in split_data


@pytest.mark.asyncio
async def test_auth_public_register_and_reset(client: AsyncClient):
    # 1. Public register
    reg_payload = {
        "email": "newvolunteer@panchayat.org",
        "password": "SecurePassword123!",
        "first_name": "Sunil",
        "last_name": "Kumar",
        "phone": "+919876543210",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    assert reg_res.json()["success"] is True
    assert reg_res.json()["data"]["email"] == "newvolunteer@panchayat.org"

    # 2. Forgot password
    forgot_res = await client.post("/api/v1/auth/forgot-password", json={"email": "newvolunteer@panchayat.org"})
    assert forgot_res.status_code == 200
    assert forgot_res.json()["success"] is True

    # 3. Reset password
    reset_res = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "sample-reset-token", "new_password": "NewSecurePassword123!"},
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["success"] is True
