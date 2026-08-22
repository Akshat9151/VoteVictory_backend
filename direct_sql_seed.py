import psycopg2
from app.core.security import get_password_hash
import uuid
from datetime import datetime, timezone

direct_url = "postgresql://neondb_owner:npg_TE0NKq7cybUL@ep-round-sky-axhqcmbx.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require"

print("1. Connecting to Neon PostgreSQL via raw psycopg2...")
conn = psycopg2.connect(direct_url, connect_timeout=15)
conn.autocommit = True
cur = conn.cursor()

print("2. Recreating clean public schema...")
cur.execute("DROP SCHEMA public CASCADE;")
cur.execute("CREATE SCHEMA public;")
cur.execute("GRANT ALL ON SCHEMA public TO neondb_owner;")
cur.execute("GRANT ALL ON SCHEMA public TO public;")

print("3. Creating tables...")
cur.execute("""
CREATE TABLE organizations (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(128) UNIQUE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    subscription_plan VARCHAR(32) NOT NULL DEFAULT 'FREE',
    contact_email VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(50),
    settings_json TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE roles (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) NOT NULL,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE permissions (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    module VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE role_permissions (
    role_id VARCHAR(36) REFERENCES roles(id) ON DELETE CASCADE,
    permission_id VARCHAR(36) REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE SET NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    ward VARCHAR(150) DEFAULT 'All Wards',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret VARCHAR(64),
    recovery_codes_json TEXT,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_roles (
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    role_id VARCHAR(36) REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE user_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    refresh_token_hash VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    device_fingerprint VARCHAR(255),
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE elections (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    title VARCHAR(255) NOT NULL,
    election_type VARCHAR(64) NOT NULL DEFAULT 'Gram Panchayat',
    state VARCHAR(100) NOT NULL DEFAULT 'Rajasthan',
    district VARCHAR(100),
    block VARCHAR(100),
    panchayat_name VARCHAR(150),
    ward_count INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    polling_date DATE,
    budget_limit NUMERIC(12, 2) NOT NULL DEFAULT 150000.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE candidates (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    election_id VARCHAR(36) REFERENCES elections(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    hindi_name VARCHAR(255),
    post_name VARCHAR(100) NOT NULL DEFAULT 'Sarpanch',
    ward_or_area VARCHAR(150),
    symbol_name VARCHAR(100),
    symbol VARCHAR(512),
    photo_url VARCHAR(512),
    slogan VARCHAR(500),
    manifesto_points TEXT,
    contact_phone VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE voters (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    election_id VARCHAR(36) REFERENCES elections(id) ON DELETE SET NULL,
    epic_number VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    relative_name VARCHAR(255),
    relation_type VARCHAR(50),
    age INTEGER,
    gender VARCHAR(16),
    ward VARCHAR(100),
    booth_number VARCHAR(50),
    house_number VARCHAR(100),
    mobile VARCHAR(50),
    is_mobile_verified BOOLEAN NOT NULL DEFAULT FALSE,
    preferred_language VARCHAR(10) NOT NULL DEFAULT 'hi',
    consent_received BOOLEAN NOT NULL DEFAULT TRUE,
    support_status VARCHAR(32) NOT NULL DEFAULT 'UNDECIDED',
    is_influencer BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    slip_distributed BOOLEAN NOT NULL DEFAULT FALSE,
    slip_distributed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE tasks (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    election_id VARCHAR(36) REFERENCES elections(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(64) NOT NULL DEFAULT 'GENERAL',
    ward_or_booth VARCHAR(150),
    priority VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    deadline DATE,
    assigned_to_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    created_by_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE expenses (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    election_id VARCHAR(36) REFERENCES elections(id) ON DELETE CASCADE NOT NULL,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    vendor_name VARCHAR(255),
    payment_mode VARCHAR(64) NOT NULL DEFAULT 'CASH',
    receipt_url VARCHAR(512),
    note TEXT,
    logged_by_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE complaints (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    election_id VARCHAR(36) REFERENCES elections(id) ON DELETE SET NULL,
    ticket_number VARCHAR(32) UNIQUE NOT NULL,
    title VARCHAR(255),
    complainant_name VARCHAR(255) NOT NULL,
    reported_by_phone VARCHAR(50),
    ward_or_location VARCHAR(150),
    category VARCHAR(64) NOT NULL DEFAULT 'OTHER',
    severity VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    description TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    assigned_to_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    created_by_user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    resolution_notes TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE field_activity_logs (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    election_id VARCHAR(36) REFERENCES elections(id) ON DELETE SET NULL,
    volunteer_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    activity_type VARCHAR(64) NOT NULL,
    title VARCHAR(255),
    ward VARCHAR(100),
    notes TEXT,
    gps_lat NUMERIC(10, 7),
    gps_lng NUMERIC(10, 7),
    voters_contacted_count INTEGER NOT NULL DEFAULT 0,
    slips_distributed_count INTEGER NOT NULL DEFAULT 0,
    proof_photo_url VARCHAR(512),
    submitted_by VARCHAR(64),
    submitted_by_role VARCHAR(30) DEFAULT 'VOLUNTEER',
    reviewed_by VARCHAR(64),
    reviewed_at TIMESTAMPTZ,
    rejection_reason TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'SUBMITTED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE design_templates (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    election_type VARCHAR(64) NOT NULL DEFAULT 'panchayat',
    category VARCHAR(64) NOT NULL DEFAULT 'poster',
    format_name VARCHAR(64) NOT NULL DEFAULT 'Election Poster',
    format_dims VARCHAR(64) NOT NULL DEFAULT '1149 x 1369 px',
    layout_json TEXT NOT NULL,
    thumbnail_url VARCHAR(512),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    display_order INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE saved_designs (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    template_id VARCHAR(36) REFERENCES design_templates(id) ON DELETE SET NULL,
    candidate_id VARCHAR(36) REFERENCES candidates(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    layout_data JSONB NOT NULL,
    rendered_image_url VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE poster_shares (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE,
    saved_design_id VARCHAR(36) REFERENCES saved_designs(id) ON DELETE SET NULL,
    shared_by_user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    platform VARCHAR(32) NOT NULL,
    share_url VARCHAR(512),
    caption TEXT,
    shared_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE broadcast_groups (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    name VARCHAR(255) NOT NULL,
    filter_criteria_snapshot TEXT NOT NULL,
    created_by VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    message_text TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
    excluded_no_contact INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE broadcast_group_members (
    id VARCHAR(36) PRIMARY KEY,
    group_id VARCHAR(36) REFERENCES broadcast_groups(id) ON DELETE CASCADE NOT NULL,
    voter_id VARCHAR(36) REFERENCES voters(id) ON DELETE CASCADE NOT NULL,
    mobile VARCHAR(50) NOT NULL,
    contact_method VARCHAR(16) NOT NULL DEFAULT 'WHATSAPP',
    voter_name VARCHAR(255) NOT NULL,
    ward VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE broadcast_logs (
    id VARCHAR(36) PRIMARY KEY,
    group_id VARCHAR(36) REFERENCES broadcast_groups(id) ON DELETE CASCADE NOT NULL,
    voter_id VARCHAR(36) REFERENCES voters(id) ON DELETE SET NULL,
    mobile VARCHAR(50) NOT NULL,
    channel_used VARCHAR(16) NOT NULL DEFAULT 'WHATSAPP',
    status VARCHAR(16) NOT NULL DEFAULT 'SENT',
    provider_response TEXT,
    sent_at VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE alembic_version (
    version_num VARCHAR(255) NOT NULL PRIMARY KEY
);
INSERT INTO alembic_version (version_num) VALUES ('5ba06aedc5cc');
""")

print("4. Seeding Super Admin Role & User...")
super_role_id = str(uuid.uuid4())
cur.execute("INSERT INTO roles (id, name, code, is_system, description) VALUES (%s, %s, %s, %s, %s);", 
            (super_role_id, 'Super Administrator', 'SUPER_ADMIN', True, 'Full unrestricted platform access.'))

super_user_id = str(uuid.uuid4())
password_hash = get_password_hash("SuperSecureAdminPassword123!")

cur.execute("""
INSERT INTO users (
    id, email, phone, password_hash, first_name, last_name, ward, 
    is_active, is_verified, is_superuser, mfa_enabled, failed_login_attempts
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
""", (
    super_user_id,
    "superadmin@electwin.com",
    "+91 98290 14285",
    password_hash,
    "Super",
    "Administrator",
    "All Wards",
    True,
    True,
    True,
    False,
    0
))

cur.execute("INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s);", (super_user_id, super_role_id))

print("5. Verifying user in Neon DB...")
cur.execute("SELECT id, email, first_name, last_name, is_superuser, password_hash FROM users;")
user_row = cur.fetchone()
print("  -> SUPERADMIN RECORD:", user_row)

cur.close()
conn.close()
print("SUCCESS! Neon database completely initialized with perfect schema and Super Admin!")
