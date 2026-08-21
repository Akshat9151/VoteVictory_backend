import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.user import User


@pytest.mark.asyncio
async def test_volunteer_can_create_and_share_poster_to_cross_roles(client: AsyncClient, db_session, volunteer_token: str, admin_token: str, superadmin_token: str):
    volunteer_headers = {"Authorization": f"Bearer {volunteer_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    superadmin_headers = {"Authorization": f"Bearer {superadmin_token}"}

    design_payload = {
        "template_id": "tpl-1",
        "title": "Volunteer Poster",
        "form_data": {"candidateName": "Rohit Sharma", "position": "Ward Member", "wardNo": "12", "ballotNo": "A3"},
        "preview_image_url": "https://example.com/poster.png",
    }

    create_design = await client.post("/api/v1/design-templates/designs", json=design_payload, headers=volunteer_headers)
    assert create_design.status_code == 201, create_design.text
    poster_id = create_design.json()["data"]["id"]

    admin_user = (await db_session.execute(select(User).where(User.email == "orgadmin@apex.org"))).scalars().first()
    superadmin_user = (await db_session.execute(select(User).where(User.email == "superadmin@electwin.com"))).scalars().first()

    share_res = await client.post(
        f"/api/v1/posters/{poster_id}/share",
        json={"recipient_ids": [admin_user.id, superadmin_user.id]},
        headers=volunteer_headers,
    )
    assert share_res.status_code == 200, share_res.text

    shared_for_admin = await client.get("/api/v1/posters/shared-with-me", headers=admin_headers)
    assert shared_for_admin.status_code == 200
    assert any(item["id"] == poster_id for item in shared_for_admin.json()["data"])

    shared_for_superadmin = await client.get("/api/v1/posters/shared-with-me", headers=superadmin_headers)
    assert shared_for_superadmin.status_code == 200
    assert any(item["id"] == poster_id for item in shared_for_superadmin.json()["data"])

    invalid_share = await client.post(
        f"/api/v1/posters/{poster_id}/share",
        json={"recipient_ids": [admin_user.id, (await db_session.execute(select(User).where(User.email == "fieldvolunteer@apex.org"))).scalars().first().id]},
        headers=volunteer_headers,
    )
    assert invalid_share.status_code == 400
