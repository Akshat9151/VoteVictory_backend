import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.permissions import DEFAULT_ROLE_PERMISSIONS, PermissionCode, RoleCode
from app.core.security import get_password_hash
from app.models.area import Booth
from app.models.broadcast import DeliveryLog
from app.models.candidate import Candidate
from app.models.complaint import Complaint
from app.models.design_template import DesignTemplate
from app.models.expense import Expense
from app.models.organization import Organization, OrganizationStatus
from app.models.team import TeamMember, Volunteer
from app.models.user import Permission, Role, RolePermission, User, UserRole
from app.models.volunteer_voter import VolunteerVoter
from app.models.voter import Voter

logger = logging.getLogger("app.bootstrap")


async def seed_system_data(db: AsyncSession) -> None:
    """Seeds initial permissions, roles, and default Super Admin if not present."""
    # 1. Seed Permissions
    existing_perms = set((await db.execute(select(Permission.code))).scalars().all())
    for perm_code in PermissionCode:
        code_str = perm_code.value
        if code_str not in existing_perms:
            module_name = code_str.split(".")[0] if "." in code_str else "system"
            perm = Permission(
                code=code_str,
                name=code_str.replace(".", " ").replace("_", " ").title(),
                module=module_name,
                description=f"Permission to perform {code_str} actions"
            )
            db.add(perm)
    await db.flush()

    # Query all permissions mapped by code
    all_perms_map = {
        p.code: p
        for p in (await db.execute(select(Permission))).scalars().all()
    }

    # 2. Seed System Roles & Role Permissions
    for role_code, perm_enums in DEFAULT_ROLE_PERMISSIONS.items():
        stmt = select(Role).where(Role.code == role_code.value, Role.is_system == True)
        role = (await db.execute(stmt)).scalars().first()
        if not role:
            role = Role(
                name=role_code.value.replace("_", " ").title(),
                code=role_code.value,
                is_system=True,
                description=f"Standard system role for {role_code.value}"
            )
            db.add(role)
            await db.flush()

            # Attach permissions
            for p_enum in perm_enums:
                perm_obj = all_perms_map.get(p_enum.value)
                if perm_obj:
                    rp = RolePermission(role_id=role.id, permission_id=perm_obj.id)
                    db.add(rp)
            await db.flush()

    # 3. Seed Default Organization
    org_stmt = select(Organization).limit(1)
    org = (await db.execute(org_stmt)).scalars().first()
    if not org:
        org = Organization(
            name="Gram Panchayat Rampur Election 2026",
            slug="gram-panchayat-rampur",
            status=OrganizationStatus.ACTIVE if hasattr(OrganizationStatus, "ACTIVE") else "ACTIVE"
        )
        db.add(org)
        await db.flush()

    # 4. Seed Super Admin User
    admin_email = settings.FIRST_SUPER_ADMIN_EMAIL.lower().strip()
    admin_stmt = select(User).where(User.email == admin_email)
    existing_admin = (await db.execute(admin_stmt)).scalars().first()

    if not existing_admin:
        logger.info(f"Bootstrapping default Super Admin: {admin_email}")
        super_admin = User(
            organization_id=org.id,
            email=admin_email,
            first_name=settings.FIRST_SUPER_ADMIN_FIRST_NAME,
            last_name=settings.FIRST_SUPER_ADMIN_LAST_NAME,
            phone="+91 98290 14285",
            password_hash=get_password_hash(settings.FIRST_SUPER_ADMIN_PASSWORD),
            is_active=True,
            is_verified=True,
            is_superuser=True
        )
        db.add(super_admin)
        await db.flush()

        # Assign SUPER_ADMIN role
        super_role_stmt = select(Role).where(Role.code == RoleCode.SUPER_ADMIN.value)
        super_role = (await db.execute(super_role_stmt)).scalars().first()
        if super_role:
            ur = UserRole(user_id=super_admin.id, role_id=super_role.id)
            db.add(ur)
        await db.flush()

    # 5. Seed Candidates if empty
    cand_stmt = select(Candidate).where(Candidate.organization_id == org.id).limit(1)
    if not (await db.execute(cand_stmt)).scalars().first():
        candidates = [
            Candidate(
                organization_id=org.id,
                name="Rameshwar Patel",
                hindiName="रामेश्वर पटेल",
                post="Sarpanch (Gram Panchayat)",
                postType="sarpanch",
                constituency="Gram Panchayat Rampur (Ward 04)",
                symbol="🚜",
                symbolName="Tractor (ट्रैक्टर)",
                photo="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&auto=format&fit=crop&q=80",
                slogan="गांव का समग्र विकास, हर घर विश्वास और खुशहाली!",
                votersCount=3500,
                volunteersCount=24,
                manifesto="1. Clean 24x7 drinking water pipeline\n2. Concrete roads & covered drainage"
            ),
            Candidate(
                organization_id=org.id,
                name="Vikram Singh Gurjar",
                hindiName="विक्रम सिंह गुर्जर",
                post="Panch (Ward)",
                postType="panch",
                constituency="Ward 02 – Patel Basti",
                symbol="🌾",
                symbolName="Farmer (किसान)",
                photo="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&auto=format&fit=crop&q=80",
                slogan="युवा नेतृत्व, स्वच्छ पेयजल और पक्की सड़कें!",
                votersCount=620,
                volunteersCount=8,
                manifesto="1. Paved concrete lane in Patel Basti"
            ),
            Candidate(
                organization_id=org.id,
                name="Savitri Bai Meena",
                hindiName="सावित्री बाई मीणा",
                post="Panch (Ward)",
                postType="panch",
                constituency="Ward 04 – Anganwadi Block",
                symbol="☀️",
                symbolName="Sun (सूरज)",
                photo="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&auto=format&fit=crop&q=80",
                slogan="नारी सशक्तिकरण, बालिका शिक्षा और बेहतर स्वास्थ्य!",
                votersCount=850,
                volunteersCount=6,
                manifesto="1. Anganwadi center upgrade"
            )
        ]
        db.add_all(candidates)

    # 6. Seed Voters if empty
    voter_stmt = select(Voter).limit(1)
    if not (await db.execute(voter_stmt)).scalars().first():
        voters = [
            Voter(id="V-04-101", voter_id_number="V-04-101", organization_id=org.id, name="Rameshwar Patel", age=48, gender="Male", ward="Ward 04", mobile="+91 98290 14285", channel="WhatsApp", consent="Verified", source="Official Roll", status="Valid"),
            Voter(id="V-04-102", voter_id_number="V-04-102", organization_id=org.id, name="Sita Devi Patel", age=42, gender="Female", ward="Ward 04", mobile="+91 98290 14286", channel="WhatsApp", consent="Verified", source="Official Roll", status="Valid"),
            Voter(id="V-02-103", voter_id_number="V-02-103", organization_id=org.id, name="Gopal Lal Gurjar", age=58, gender="Male", ward="Ward 02", mobile="+91 97840 55190", channel="SMS Only", consent="Pending", source="Booth Survey", status="Valid"),
            Voter(id="V-02-104", voter_id_number="V-02-104", organization_id=org.id, name="Kamla Devi Gurjar", age=38, gender="Female", ward="Ward 02", mobile="+91 96021 44556", channel="WhatsApp", consent="Verified", source="OCR Scan", status="Valid"),
            Voter(id="V-01-105", voter_id_number="V-01-105", organization_id=org.id, name="Rahul Sharma", age=22, gender="Male", ward="Ward 01", mobile="+91 94140 11920", channel="WhatsApp", consent="Verified", source="Youth Drive", status="Valid"),
            Voter(id="V-04-106", voter_id_number="V-04-106", organization_id=org.id, name="Kavita Meena", age=24, gender="Female", ward="Ward 04", mobile="+91 98288 33119", channel="WhatsApp", consent="Verified", source="Women SHG", status="Valid"),
            Voter(id="V-03-107", voter_id_number="V-03-107", organization_id=org.id, name="Suraj Mal Jat", age=65, gender="Male", ward="Ward 03", mobile="", channel="SMS Only", consent="Missing Mobile", source="Official Roll", status="Missing Mobile"),
            Voter(id="V-02-108", voter_id_number="V-02-108", organization_id=org.id, name="Sunil Kumar Gurjar", age=21, gender="Male", ward="Ward 02", mobile="+91 96021 77890", channel="WhatsApp", consent="Verified", source="Youth Drive", status="Valid"),
            Voter(id="V-04-109", voter_id_number="V-04-109", organization_id=org.id, name="Manju Devi Saini", age=35, gender="Female", ward="Ward 04", mobile="+91 94140 88219", channel="WhatsApp", consent="Verified", source="Women SHG", status="Valid"),
            Voter(id="V-01-110", voter_id_number="V-01-110", organization_id=org.id, name="Babulal Prajapat", age=52, gender="Male", ward="Ward 01", mobile="+91 98290 66451", channel="SMS Only", consent="Verified", source="Official Roll", status="Valid")
        ]
        db.add_all(voters)

    # 7. Seed Team & Volunteers
    team_stmt = select(TeamMember).where(TeamMember.organization_id == org.id).limit(1)
    if not (await db.execute(team_stmt)).scalars().first():
        team = [
            TeamMember(id="team_01", organization_id=org.id, name="Rameshwar Patel", role="Super Admin", roleTitle="Contesting Candidate (Owner)", ward="All Wards (Gram Panchayat Rampur)", phone="+91 98290 14285", status="Active", votersHandled=3500, addedDate="01 Aug 2026"),
            TeamMember(id="team_02", organization_id=org.id, name="Rajesh Kumar Sharma", role="Admin", roleTitle="Campaign Operations Manager", ward="All Wards (Campaign HQ)", phone="+91 94140 33812", status="Active", votersHandled=1850, addedDate="03 Aug 2026"),
            TeamMember(id="team_03", organization_id=org.id, name="Priya Sharma", role="Admin", roleTitle="Social Media & Broadcast Coordinator", ward="All Wards (Digital Cell)", phone="+91 98288 99120", status="Active", votersHandled=2850, addedDate="06 Aug 2026"),
            TeamMember(id="team_04", organization_id=org.id, name="Kailash Saini", role="Volunteer", roleTitle="Booth 02 Incharge (Panna Pramukh)", ward="Ward 02 – Patel Basti", phone="+91 97840 55190", status="Active", votersHandled=45, addedDate="08 Aug 2026"),
            TeamMember(id="team_05", organization_id=org.id, name="Mukesh Gurjar", role="Volunteer", roleTitle="Booth 01 Incharge (Youth Mobilizer)", ward="Ward 04 – Rampur HQ", phone="+91 94140 88219", status="Active", votersHandled=38, addedDate="10 Aug 2026"),
            TeamMember(id="team_06", organization_id=org.id, name="Anita Kumari", role="Volunteer", roleTitle="Women SHG Field Lead", ward="Ward 01 – Old Village", phone="+91 96021 66723", status="Active", votersHandled=29, addedDate="12 Aug 2026")
        ]
        db.add_all(team)

        volunteers = [
            Volunteer(id="vol_1", organization_id=org.id, name="Kailash Saini", role="Ward 02 Incharge", ward="Ward 02 (Booth 02 - Community Hall)", phone="+91 94140 22910", votersAdded=450, callsMade=320, slipsDistributed=540, status="Active"),
            Volunteer(id="vol_2", organization_id=org.id, name="Priya Sharma", role="Women SHG Coordinator", ward="Ward 04 (Booth 01 - Govt School)", phone="+91 98288 12455", votersAdded=620, callsMade=480, slipsDistributed=680, status="Active"),
            Volunteer(id="vol_3", organization_id=org.id, name="Mukesh Gurjar", role="Youth Mobilizer", ward="Ward 01 (Booth 03 - Panchayat Bhawan)", phone="+91 96021 55901", votersAdded=380, callsMade=290, slipsDistributed=420, status="Active"),
            Volunteer(id="vol_4", organization_id=org.id, name="Mahesh Sharma", role="Booth 04 Incharge", ward="Ward 03 (Booth 04 - Anganwadi Center)", phone="+91 94140 77123", votersAdded=310, callsMade=210, slipsDistributed=390, status="On-Duty")
        ]
        db.add_all(volunteers)

    # 8. Seed Expenses
    exp_stmt = select(Expense).where(Expense.organization_id == org.id).limit(1)
    if not (await db.execute(exp_stmt)).scalars().first():
        expenses = [
            Expense(id="exp_01", organization_id=org.id, category="Pamphlet & Banner Printing", amount=24500.0, date="14 Aug 2026", note="Rampur Digital Flex Print (500 Pamphlets, 4 Hoardings)", mode="UPI / Online", user="Rajesh Kumar (Admin)"),
            Expense(id="exp_02", organization_id=org.id, category="Sound, DJ & Mic Rental", amount=12000.0, date="12 Aug 2026", note="Shree Ram Sound Service (Nukkad Sabha Ward 02 & 04)", mode="Cash Voucher", user="Rameshwar Patel (Candidate)"),
            Expense(id="exp_03", organization_id=org.id, category="Tea, Snacks & Volunteer Food", amount=14250.0, date="10 Aug 2026", note="Chai & Snacks for 24 Panna Pramukhs across 6 Booths", mode="UPI / Online", user="Rajesh Kumar (Admin)"),
            Expense(id="exp_04", organization_id=org.id, category="Vehicle Fuel & Transport", amount=11500.0, date="08 Aug 2026", note="Campaign Bolero diesel (Ward 01 to 06 village tour)", mode="Cash Voucher", user="Kailash Saini (Volunteer)"),
            Expense(id="exp_05", organization_id=org.id, category="Office & Panna Supplies", amount=6200.0, date="05 Aug 2026", note="Voter roll stationery, clipboards, pens & identity cards", mode="UPI / Online", user="Rajesh Kumar (Admin)")
        ]
        db.add_all(expenses)

    # 9. Seed Complaints
    comp_stmt = select(Complaint).where(Complaint.organization_id == org.id).limit(1)
    if not (await db.execute(comp_stmt)).scalars().first():
        complaints = [
            Complaint(id="GR-101", organization_id=org.id, name="Suraj Mal Sharma", ward="Ward 04", category="Water Supply", desc="Handpump non-functional near community well; water pipeline pressure low", date="15 Aug 2026", status="In Progress"),
            Complaint(id="GR-102", organization_id=org.id, name="Kavita Meena", ward="Ward 04", category="Health / School", desc="Primary health sub-center ANM nurse not available on Tuesdays", date="14 Aug 2026", status="Open"),
            Complaint(id="GR-103", organization_id=org.id, name="Gopal Lal Gurjar", ward="Ward 02", category="Road Drainage", desc="Rainwater stagnation in front of primary school; drainage culvert choked", date="12 Aug 2026", status="Resolved"),
            Complaint(id="GR-104", organization_id=org.id, name="Sunil Kumar", ward="Ward 02", category="Electricity", desc="Low voltage during evening 6 to 9 PM; tube well pump trip issue", date="10 Aug 2026", status="In Progress"),
            Complaint(id="GR-105", organization_id=org.id, name="Babulal Prajapat", ward="Ward 01", category="Road Drainage", desc="Kaccha road needs gravel paving before polling day", date="08 Aug 2026", status="Open")
        ]
        db.add_all(complaints)

    # 10. Seed Volunteer Canvassing Voters
    vv_stmt = select(VolunteerVoter).where(VolunteerVoter.organization_id == org.id).limit(1)
    if not (await db.execute(vv_stmt)).scalars().first():
        vvoters = [
            VolunteerVoter(id="V-02-101", organization_id=org.id, name="Gopal Lal Gurjar", age=58, mobile="+91 97840 55190", house="House #14, Patel Chowk", status="Visited", slipHanded=True),
            VolunteerVoter(id="V-02-102", organization_id=org.id, name="Kamla Devi Gurjar", age=38, mobile="+91 96021 44556", house="House #19, Basti Lane 2", status="Called", slipHanded=True),
            VolunteerVoter(id="V-02-103", organization_id=org.id, name="Vikram Singh Jat", age=31, mobile="+91 94140 99881", house="House #22, Near Water Tank", status="Visited", slipHanded=True),
            VolunteerVoter(id="V-02-104", organization_id=org.id, name="Mohan Lal Saini", age=45, mobile="+91 98290 33412", house="House #08, Main Chowk", status="Pending", slipHanded=False),
            VolunteerVoter(id="V-02-105", organization_id=org.id, name="Shanti Devi", age=52, mobile="+91 94140 11920", house="House #31, School Road", status="Called", slipHanded=True),
            VolunteerVoter(id="V-02-106", organization_id=org.id, name="Sunil Kumar Gurjar", age=24, mobile="+91 96021 77890", house="House #11, Basti Lane 1", status="Not Reachable", slipHanded=False)
        ]
        db.add_all(vvoters)

    # 11. Seed Delivery Logs
    log_stmt = select(DeliveryLog).where(DeliveryLog.organization_id == org.id).limit(1)
    if not (await db.execute(log_stmt)).scalars().first():
        logs = [
            DeliveryLog(id="1", organization_id=org.id, name="Rameshwar Patel", ward="Ward 04", mobile="+91 98290 14285", route="WhatsApp", status="Delivered", read="Read (Blue Tick)", time="10:45 AM"),
            DeliveryLog(id="2", organization_id=org.id, name="Sita Devi Patel", ward="Ward 04", mobile="+91 98290 14286", route="WhatsApp", status="Delivered", read="Read (Blue Tick)", time="10:45 AM"),
            DeliveryLog(id="3", organization_id=org.id, name="Gopal Lal Gurjar", ward="Ward 02", mobile="+91 97840 55190", route="SMS Fallback", status="Delivered", read="N/A (SMS)", time="10:46 AM"),
            DeliveryLog(id="4", organization_id=org.id, name="Kamla Devi Gurjar", ward="Ward 02", mobile="+91 96021 44556", route="WhatsApp", status="Delivered", read="Delivered ✓✓", time="10:46 AM"),
            DeliveryLog(id="5", organization_id=org.id, name="Rahul Sharma", ward="Ward 01", mobile="+91 94140 11920", route="WhatsApp", status="Delivered", read="Read (Blue Tick)", time="10:47 AM"),
            DeliveryLog(id="6", organization_id=org.id, name="Suraj Mal Jat", ward="Ward 03", mobile="+91 94140 00000", route="SMS Fallback", status="Delivered", read="N/A (SMS)", time="10:48 AM")
        ]
        db.add_all(logs)

    # 12. Seed Booths
    booth_stmt = select(Booth).where(Booth.organization_id == org.id).limit(1)
    if not (await db.execute(booth_stmt)).scalars().first():
        booths = [
            Booth(organization_id=org.id, booth_number="Booth 01", boothNo="Booth 01", location="Govt Senior Secondary School, Rampur", incharge="Rajesh Kumar (+91 98290 14285)", voters=850, slips=748, coverage="88%"),
            Booth(organization_id=org.id, booth_number="Booth 02", boothNo="Booth 02", location="Panchayat Community Hall, Patel Basti", incharge="Kailash Saini (+91 94140 22910)", voters=620, slips=570, coverage="92%"),
            Booth(organization_id=org.id, booth_number="Booth 03", boothNo="Booth 03", location="Gram Panchayat Bhawan, Main Road", incharge="Mukesh Gurjar (+91 96021 55901)", voters=580, slips=490, coverage="84%"),
            Booth(organization_id=org.id, booth_number="Booth 04", boothNo="Booth 04", location="Anganwadi Center No. 2, Ward 03", incharge="Mahesh Sharma (+91 94140 77123)", voters=510, slips=420, coverage="82%"),
            Booth(organization_id=org.id, booth_number="Booth 05", boothNo="Booth 05", location="Primary Health Sub-Center, Ward 05", incharge="Suraj Bhan Meena (+91 97840 44109)", voters=480, slips=410, coverage="85%"),
            Booth(organization_id=org.id, booth_number="Booth 06", boothNo="Booth 06", location="Cooperative Society Hall, Ward 06", incharge="Dinesh Yadav (+91 98288 33110)", voters=460, slips=390, coverage="84%")
        ]
        db.add_all(booths)

    # 13. Seed Design Studio Templates
    tmpl_stmt = select(DesignTemplate).limit(1)
    if not (await db.execute(tmpl_stmt)).scalars().first():
        templates = [
            DesignTemplate(
                id="template-poster-tricolor",
                organization_id=org.id,
                name="Tricolor Poster – Portrait",
                election_type="panchayat",
                category="poster",
                format_name="A4 Poster",
                format_dims="210 × 297 mm",
                thumbnail_url="https://images.unsplash.com/photo-1589939705066-5ec8b3b47f1d?w=200&h=280&crop=faces&fit=crop",
                is_active=True,
                display_order=1,
                layout_json={
                    "bg_color": "#ffffff",
                    "width": 600,
                    "height": 848,
                    "elements": [
                        {"type": "shape", "x": 0, "y": 0, "width": 600, "height": 130, "color": "#ff9933", "value": "tricolor-top", "z_index": 1},
                        {"type": "shape", "x": 0, "y": 130, "width": 600, "height": 130, "color": "#ffffff", "value": "tricolor-mid", "z_index": 1},
                        {"type": "shape", "x": 0, "y": 260, "width": 600, "height": 130, "color": "#138808", "value": "tricolor-bot", "z_index": 1},
                        {"type": "text", "x": 10, "y": 350, "width": 580, "height": 80, "placeholder": "{{candidate_name}}", "font_size": 48, "font_weight": "bold", "color": "#000000", "z_index": 3},
                        {"type": "text", "x": 10, "y": 430, "width": 580, "height": 60, "placeholder": "{{position}}", "font_size": 32, "color": "#333333", "z_index": 3},
                        {"type": "symbol", "x": 450, "y": 320, "width": 120, "height": 120, "placeholder": "{{symbol}}", "z_index": 4},
                        {"type": "text", "x": 10, "y": 500, "width": 580, "height": 100, "placeholder": "{{slogan}}", "font_size": 24, "font_weight": "bold", "color": "#ff6b00", "text_align": "center", "z_index": 3},
                        {"type": "text", "x": 10, "y": 620, "width": 580, "height": 50, "value": "Campaign 2026", "font_size": 16, "color": "#666666", "text_align": "center", "z_index": 3}
                    ]
                }
            ),
            DesignTemplate(
                id="template-banner-landscape",
                organization_id=org.id,
                name="Campaign Banner – Landscape",
                election_type="panchayat",
                category="banner",
                format_name="Hoarding Banner",
                format_dims="1200 × 600 px",
                thumbnail_url="https://images.unsplash.com/photo-1585647347384-2593bc35786b?w=300&h=150&crop=faces&fit=crop",
                is_active=True,
                display_order=2,
                layout_json={
                    "bg_color": "#0f172a",
                    "width": 1200,
                    "height": 600,
                    "elements": [
                        {"type": "text", "x": 20, "y": 50, "width": 550, "height": 150, "placeholder": "{{candidate_name}}", "font_size": 64, "font_weight": "bold", "color": "#ffffff", "z_index": 2},
                        {"type": "photo", "x": 50, "y": 150, "width": 400, "height": 400, "placeholder": "candidate_photo", "z_index": 1},
                        {"type": "symbol", "x": 600, "y": 150, "width": 200, "height": 200, "placeholder": "{{symbol}}", "z_index": 3},
                        {"type": "text", "x": 600, "y": 380, "width": 550, "height": 150, "placeholder": "{{slogan}}", "font_size": 40, "font_weight": "bold", "color": "#fbbf24", "text_align": "center", "z_index": 2}
                    ]
                }
            ),
            DesignTemplate(
                id="template-idcard-small",
                organization_id=org.id,
                name="ID Card – Vertical",
                election_type="panchayat",
                category="id_card",
                format_name="ID Card",
                format_dims="90 × 150 mm",
                thumbnail_url="https://images.unsplash.com/photo-1549887534-f3d6f6a8f5a0?w=90&h=150&crop=faces&fit=crop",
                is_active=True,
                display_order=3,
                layout_json={
                    "bg_color": "#1e293b",
                    "width": 350,
                    "height": 560,
                    "elements": [
                        {"type": "photo", "x": 20, "y": 20, "width": 310, "height": 200, "placeholder": "candidate_photo", "z_index": 1},
                        {"type": "text", "x": 10, "y": 240, "width": 330, "height": 60, "placeholder": "{{candidate_name}}", "font_size": 28, "font_weight": "bold", "color": "#ffffff", "text_align": "center", "z_index": 2},
                        {"type": "text", "x": 10, "y": 300, "width": 330, "height": 40, "placeholder": "{{position}}", "font_size": 18, "color": "#94a3b8", "text_align": "center", "z_index": 2},
                        {"type": "symbol", "x": 125, "y": 360, "width": 100, "height": 100, "placeholder": "{{symbol}}", "z_index": 3},
                        {"type": "text", "x": 10, "y": 480, "width": 330, "height": 40, "placeholder": "{{contact}}", "font_size": 14, "color": "#cbd5e1", "text_align": "center", "z_index": 2}
                    ]
                }
            ),
            DesignTemplate(
                id="template-social-square",
                organization_id=org.id,
                name="Social Card – Square (Instagram/WhatsApp)",
                election_type="panchayat",
                category="social",
                format_name="Square Post",
                format_dims="1080 × 1080 px",
                thumbnail_url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=200&h=200&crop=faces&fit=crop",
                is_active=True,
                display_order=4,
                layout_json={
                    "bg_color": "#064e3b",
                    "width": 600,
                    "height": 600,
                    "elements": [
                        {"type": "shape", "x": 20, "y": 20, "width": 560, "height": 560, "border_color": "#10b981", "border_width": 2, "border_radius": 16, "z_index": 1},
                        {"type": "text", "x": 30, "y": 60, "width": 540, "height": 70, "placeholder": "{{candidate_name}}", "font_size": 42, "font_weight": "bold", "color": "#ffffff", "text_align": "center", "z_index": 2},
                        {"type": "text", "x": 30, "y": 140, "width": 540, "height": 50, "placeholder": "{{position}}", "font_size": 24, "color": "#6ee7b7", "text_align": "center", "z_index": 2},
                        {"type": "symbol", "x": 230, "y": 220, "width": 140, "height": 140, "placeholder": "{{symbol}}", "z_index": 3},
                        {"type": "text", "x": 30, "y": 400, "width": 540, "height": 80, "placeholder": "{{slogan}}", "font_size": 22, "font_weight": "bold", "color": "#fef08a", "text_align": "center", "z_index": 2},
                        {"type": "text", "x": 30, "y": 500, "width": 540, "height": 40, "placeholder": "{{contact}}", "font_size": 16, "color": "#a7f3d0", "text_align": "center", "z_index": 2}
                    ]
                }
            )
        ]
        db.add_all(templates)

    await db.commit()
    logger.info("System bootstrap completed successfully.")
