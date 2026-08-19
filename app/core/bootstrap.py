import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import DEFAULT_ROLE_PERMISSIONS, PermissionCode
from app.models.design_template import DesignTemplate
from app.models.user import Permission, Role, RolePermission

logger = logging.getLogger("app.bootstrap")


async def seed_system_data(db: AsyncSession) -> None:
    """Seed only shared RBAC metadata; tenant data is created during onboarding."""
    existing_perms = set((await db.execute(select(Permission.code))).scalars().all())
    for permission_code in PermissionCode:
        code = permission_code.value
        if code not in existing_perms:
            db.add(Permission(
                code=code,
                name=code.replace(".", " ").replace("_", " ").title(),
                module=code.split(".")[0] if "." in code else "system",
                description=f"Permission to perform {code} actions",
            ))
    await db.flush()

    permissions = {
        permission.code: permission
        for permission in (await db.execute(select(Permission))).scalars().all()
    }
    for role_code, permission_codes in DEFAULT_ROLE_PERMISSIONS.items():
        role = (await db.execute(
            select(Role).where(Role.code == role_code.value, Role.is_system.is_(True))
        )).scalars().first()
        if not role:
            role = Role(
                name=role_code.value.replace("_", " ").title(),
                code=role_code.value,
                is_system=True,
                description=f"Standard system role for {role_code.value}",
            )
            db.add(role)
            await db.flush()

        existing_role_permissions = set((await db.execute(
            select(RolePermission.permission_id).where(RolePermission.role_id == role.id)
        )).scalars().all())
        for permission_code in permission_codes:
            permission = permissions.get(permission_code.value)
            if permission and permission.id not in existing_role_permissions:
                db.add(RolePermission(role_id=role.id, permission_id=permission.id))

    templates = [
        {
            "name": "Campaign Poster",
            "category": "poster",
            "format_name": "Election Poster",
            "format_dims": "1149 x 1369 px",
            "asset": "/uploads/design-templates/Poster.png",
            "width": 1149,
            "height": 1369,
            "layout": {
                "bg_color": "#ffffff",
                "width": 1149,
                "height": 1369,
                "elements": [
                    {"type": "image", "x": 0, "y": 0, "width": 1149, "height": 1369, "value": "/uploads/design-templates/Poster.png", "z_index": 0},
                    # 1. Name area mask
                    {"type": "mask", "x": 60, "y": 240, "width": 580, "height": 215, "color": "#f8f5ed", "z_index": 1},
                    # 2. Position pill mask
                    {"type": "shape", "x": 65, "y": 460, "width": 530, "height": 80, "border_radius": 20, "color": "#075902", "z_index": 1},
                    # 3. Position subtitle mask
                    {"type": "mask", "x": 65, "y": 545, "width": 530, "height": 60, "color": "#f8f5ed", "z_index": 1},
                    # 4. Symbol circle mask
                    {"type": "shape", "x": 230, "y": 660, "width": 210, "height": 210, "border_radius": 105, "color": "#ffffff", "border_color": "#f97316", "border_width": 4, "z_index": 1},
                    # 5. Symbol pill mask
                    {"type": "shape", "x": 220, "y": 835, "width": 230, "height": 50, "border_radius": 15, "color": "#075902", "z_index": 2},
                    # 6. Ward & Ballot badge number masks
                    {"type": "mask", "x": 675, "y": 805, "width": 150, "height": 90, "color": "#ffffff", "z_index": 1},
                    {"type": "mask", "x": 880, "y": 805, "width": 150, "height": 90, "color": "#ffffff", "z_index": 1},
                    # 7. Slogan mask
                    {"type": "mask", "x": 240, "y": 1175, "width": 680, "height": 65, "color": "#f8f5ed", "z_index": 1},
                    # 8. Bottom Phone mask
                    {"type": "mask", "x": 530, "y": 1260, "width": 410, "height": 85, "color": "#085305", "z_index": 1},
                    # 9. Candidate Photo
                    {"type": "photo", "x": 655, "y": 205, "width": 410, "height": 505, "border_radius": 24, "z_index": 3},
                    # 10. Logo
                    {"type": "logo", "x": 969, "y": 25, "width": 120, "height": 100, "z_index": 4},
                    # 11. Text elements
                    {"type": "text", "x": 60, "y": 260, "width": 580, "height": 45, "placeholder": "आपका अपना", "font_size": 36, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 60, "y": 320, "width": 580, "height": 110, "placeholder": "{{candidate_name}}", "font_size": 64, "font_weight": "bold", "color": "#ea580c", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 65, "y": 475, "width": 530, "height": 50, "placeholder": "{{position}}", "font_size": 40, "font_weight": "bold", "color": "#ffffff", "text_align": "center", "z_index": 4},
                    {"type": "symbol", "x": 230, "y": 660, "width": 210, "height": 175, "font_size": 84, "z_index": 4},
                    {"type": "text", "x": 220, "y": 845, "width": 230, "height": 35, "placeholder": "{{symbol_name}}", "font_size": 24, "font_weight": "bold", "color": "#ffffff", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 675, "y": 810, "width": 150, "height": 80, "placeholder": "{{ward_no}}", "font_size": 68, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 880, "y": 810, "width": 150, "height": 80, "placeholder": "{{ballot_no}}", "font_size": 68, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 240, "y": 1185, "width": 680, "height": 50, "placeholder": "{{slogan}}", "font_size": 32, "font_weight": "bold", "color": "#075902", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 530, "y": 1280, "width": 410, "height": 50, "placeholder": "{{contact}}", "font_size": 34, "font_weight": "bold", "color": "#ffffff", "text_align": "center", "z_index": 4},
                ]
            }
        },
        {
            "name": "Campaign Pamphlet",
            "category": "pamphlet",
            "format_name": "Portrait Pamphlet",
            "format_dims": "1054 x 1492 px",
            "asset": "/uploads/design-templates/poster2.png",
            "width": 1054,
            "height": 1492,
            "layout": {
                "bg_color": "#ffffff",
                "width": 1054,
                "height": 1492,
                "elements": [
                    {"type": "image", "x": 0, "y": 0, "width": 1054, "height": 1492, "value": "/uploads/design-templates/poster2.png", "z_index": 0},
                    # 1. Top Slogan mask
                    {"type": "mask", "x": 280, "y": 65, "width": 480, "height": 115, "color": "#ffffff", "z_index": 1},
                    # 2. Name area mask
                    {"type": "mask", "x": 190, "y": 465, "width": 660, "height": 150, "color": "#ffffff", "z_index": 1},
                    # 3. Position pill mask
                    {"type": "shape", "x": 225, "y": 620, "width": 590, "height": 55, "border_radius": 15, "color": "#4ba06e", "z_index": 1},
                    # 4. Position subtitle mask
                    {"type": "mask", "x": 285, "y": 678, "width": 470, "height": 40, "color": "#ffffff", "z_index": 1},
                    # 5. Symbol circle mask
                    {"type": "shape", "x": 145, "y": 215, "width": 225, "height": 225, "border_radius": 112, "color": "#ffffff", "border_color": "#3891d2", "border_width": 4, "z_index": 1},
                    # 6. Symbol pill mask
                    {"type": "shape", "x": 150, "y": 370, "width": 220, "height": 40, "border_radius": 15, "color": "#3891d2", "z_index": 2},
                    # 7. Ward & Ballot number masks
                    {"type": "mask", "x": 235, "y": 768, "width": 205, "height": 95, "color": "#ffffff", "z_index": 1},
                    {"type": "mask", "x": 556, "y": 768, "width": 208, "height": 95, "color": "#ffffff", "z_index": 1},
                    # 8. Contact mask
                    {"type": "mask", "x": 415, "y": 908, "width": 320, "height": 48, "color": "#f5fbf6", "z_index": 1},
                    # 9. Candidate Photo
                    {"type": "photo", "x": 438, "y": 238, "width": 390, "height": 450, "border_radius": 24, "z_index": 3},
                    # 10. Logo
                    {"type": "logo", "x": 874, "y": 25, "width": 120, "height": 100, "z_index": 4},
                    # 11. Text elements
                    {"type": "text", "x": 280, "y": 85, "width": 480, "height": 80, "placeholder": "{{slogan}}", "font_size": 28, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 190, "y": 475, "width": 660, "height": 40, "placeholder": "आपका अपना", "font_size": 34, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 190, "y": 525, "width": 660, "height": 80, "placeholder": "{{candidate_name}}", "font_size": 58, "font_weight": "bold", "color": "#2c82c9", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 225, "y": 630, "width": 590, "height": 40, "placeholder": "{{position}}", "font_size": 32, "font_weight": "bold", "color": "#ffffff", "text_align": "center", "z_index": 4},
                    {"type": "symbol", "x": 145, "y": 225, "width": 225, "height": 145, "font_size": 78, "z_index": 4},
                    {"type": "text", "x": 150, "y": 378, "width": 220, "height": 30, "placeholder": "{{symbol_name}}", "font_size": 22, "font_weight": "bold", "color": "#ffffff", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 235, "y": 775, "width": 205, "height": 80, "placeholder": "{{ward_no}}", "font_size": 68, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 556, "y": 775, "width": 208, "height": 80, "placeholder": "{{ballot_no}}", "font_size": 68, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 415, "y": 915, "width": 320, "height": 40, "placeholder": "{{contact}}", "font_size": 32, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                ]
            }
        },
        {
            "name": "Candidate ID Card",
            "category": "id_card",
            "format_name": "Candidate ID Card",
            "format_dims": "1536 x 1024 px",
            "asset": "/uploads/design-templates/Id Card.png",
            "width": 1536,
            "height": 1024,
            "layout": {
                "bg_color": "#ffffff",
                "width": 1536,
                "height": 1024,
                "elements": [
                    {"type": "image", "x": 0, "y": 0, "width": 1536, "height": 1024, "value": "/uploads/design-templates/Id Card.png", "z_index": 0},
                    # 1. Name mask
                    {"type": "mask", "x": 510, "y": 170, "width": 590, "height": 145, "color": "#ffffff", "z_index": 1},
                    # 2. Position pill mask
                    {"type": "shape", "x": 515, "y": 325, "width": 565, "height": 100, "border_radius": 15, "color": "#075902", "z_index": 1},
                    # 3. Position subtitle mask
                    {"type": "mask", "x": 520, "y": 435, "width": 560, "height": 70, "color": "#ffffff", "z_index": 1},
                    # 4. Symbol circle mask
                    {"type": "shape", "x": 1190, "y": 150, "width": 245, "height": 245, "border_radius": 122, "color": "#ffffff", "border_color": "#f97316", "border_width": 4, "z_index": 1},
                    # 5. Symbol pill mask
                    {"type": "shape", "x": 1230, "y": 390, "width": 165, "height": 55, "border_radius": 12, "color": "#075902", "z_index": 2},
                    # 6. Ward & Ballot masks
                    {"type": "mask", "x": 135, "y": 705, "width": 310, "height": 145, "color": "#ffffff", "z_index": 1},
                    {"type": "mask", "x": 505, "y": 705, "width": 290, "height": 145, "color": "#ffffff", "z_index": 1},
                    # 7. Phone mask
                    {"type": "mask", "x": 1010, "y": 710, "width": 440, "height": 80, "color": "#ffffff", "z_index": 1},
                    # 8. Candidate Photo
                    {"type": "photo", "x": 120, "y": 160, "width": 335, "height": 400, "border_radius": 20, "z_index": 3},
                    # 9. Logo
                    {"type": "logo", "x": 1356, "y": 25, "width": 120, "height": 100, "z_index": 4},
                    # 10. Texts
                    {"type": "text", "x": 510, "y": 190, "width": 590, "height": 110, "placeholder": "{{candidate_name}}", "font_size": 72, "font_weight": "bold", "color": "#ea580c", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 515, "y": 345, "width": 565, "height": 60, "placeholder": "{{position}}", "font_size": 46, "font_weight": "bold", "color": "#ffffff", "text_align": "center", "z_index": 4},
                    {"type": "symbol", "x": 1190, "y": 160, "width": 245, "height": 220, "font_size": 105, "z_index": 4},
                    {"type": "text", "x": 1230, "y": 400, "width": 165, "height": 40, "placeholder": "{{symbol_name}}", "font_size": 28, "font_weight": "bold", "color": "#ffffff", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 135, "y": 720, "width": 310, "height": 120, "placeholder": "{{ward_no}}", "font_size": 84, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 505, "y": 720, "width": 290, "height": 120, "placeholder": "{{ballot_no}}", "font_size": 84, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 1010, "y": 725, "width": 440, "height": 60, "placeholder": "{{contact}}", "font_size": 48, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                ]
            }
        },
        {
            "name": "Campaign Banner",
            "category": "banner",
            "format_name": "Hoarding Banner",
            "format_dims": "1774 x 887 px",
            "asset": "/uploads/design-templates/holdings.png",
            "width": 1774,
            "height": 887,
            "layout": {
                "bg_color": "#ffffff",
                "width": 1774,
                "height": 887,
                "elements": [
                    {"type": "image", "x": 0, "y": 0, "width": 1774, "height": 887, "value": "/uploads/design-templates/holdings.png", "z_index": 0},
                    # 1. Top Slogan mask
                    {"type": "mask", "x": 370, "y": 75, "width": 490, "height": 110, "color": "#ffffff", "z_index": 1},
                    # 2. Name area mask
                    {"type": "mask", "x": 345, "y": 230, "width": 645, "height": 250, "color": "#ffffff", "z_index": 1},
                    # 3. Position pill mask
                    {"type": "shape", "x": 345, "y": 495, "width": 655, "height": 100, "border_radius": 15, "color": "#075902", "z_index": 1},
                    # 4. Position subtitle mask
                    {"type": "mask", "x": 440, "y": 605, "width": 465, "height": 65, "color": "#ffffff", "z_index": 1},
                    # 5. Symbol circle mask
                    {"type": "shape", "x": 25, "y": 330, "width": 295, "height": 295, "border_radius": 147, "color": "#ffffff", "border_color": "#f97316", "border_width": 4, "z_index": 1},
                    # 6. Symbol pill mask
                    {"type": "shape", "x": 55, "y": 620, "width": 225, "height": 70, "border_radius": 15, "color": "#075902", "z_index": 2},
                    # 7. Ward & Ballot masks
                    {"type": "mask", "x": 1535, "y": 255, "width": 200, "height": 140, "color": "#ffffff", "z_index": 1},
                    {"type": "mask", "x": 1535, "y": 545, "width": 200, "height": 135, "color": "#ffffff", "z_index": 1},
                    # 8. Contact mask
                    {"type": "mask", "x": 210, "y": 870, "width": 640, "height": 90, "color": "#075902", "z_index": 1},
                    # 9. Candidate Photo
                    {"type": "photo", "x": 1060, "y": 60, "width": 410, "height": 710, "border_radius": 24, "z_index": 3},
                    # 10. Logo
                    {"type": "logo", "x": 1594, "y": 25, "width": 120, "height": 100, "z_index": 4},
                    # 11. Texts
                    {"type": "text", "x": 370, "y": 90, "width": 490, "height": 80, "placeholder": "{{slogan}}", "font_size": 32, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 345, "y": 245, "width": 645, "height": 45, "placeholder": "आपका अपना", "font_size": 40, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 345, "y": 310, "width": 645, "height": 140, "placeholder": "{{candidate_name}}", "font_size": 82, "font_weight": "bold", "color": "#ea580c", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 345, "y": 515, "width": 655, "height": 65, "placeholder": "{{position}}", "font_size": 50, "font_weight": "bold", "color": "#ffffff", "text_align": "center", "z_index": 4},
                    {"type": "symbol", "x": 25, "y": 345, "width": 295, "height": 265, "font_size": 125, "z_index": 4},
                    {"type": "text", "x": 55, "y": 632, "width": 225, "height": 48, "placeholder": "{{symbol_name}}", "font_size": 32, "font_weight": "bold", "color": "#ffffff", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 1535, "y": 270, "width": 200, "height": 110, "placeholder": "{{ward_no}}", "font_size": 88, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 1535, "y": 560, "width": 200, "height": 110, "placeholder": "{{ballot_no}}", "font_size": 88, "font_weight": "bold", "color": "#111111", "text_align": "center", "z_index": 4},
                    {"type": "text", "x": 210, "y": 885, "width": 640, "height": 60, "placeholder": "{{contact}}", "font_size": 42, "font_weight": "bold", "color": "#ffffff", "text_align": "center", "z_index": 4},
                ]
            }
        },
    ]
    existing_templates = {t.name: t for t in (await db.execute(select(DesignTemplate))).scalars().all()}
    for item in templates:
        existing = existing_templates.get(item["name"])
        if existing:
            existing.layout_json = item["layout"]
            existing.format_name = item["format_name"]
            existing.format_dims = item["format_dims"]
            existing.thumbnail_url = item["asset"]
        else:
            db.add(DesignTemplate(
                name=item["name"],
                election_type="panchayat",
                category=item["category"],
                format_name=item["format_name"],
                format_dims=item["format_dims"],
                thumbnail_url=item["asset"],
                layout_json=item["layout"],
                is_active=True,
                display_order=len(existing_templates) + 1,
            ))
    await db.commit()
    logger.info("System RBAC and Design Templates synced successfully.")

    await db.commit()
    logger.info("System RBAC ready; no demo tenant data was seeded.")