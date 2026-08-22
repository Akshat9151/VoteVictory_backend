import psycopg2
from sqlalchemy import create_engine, text
from app.core.database import Base
from app.models import *
from app.core.security import get_password_hash
import uuid

direct_sync_url = "postgresql://neondb_owner:npg_TE0NKq7cybUL@ep-round-sky-axhqcmbx.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require"

print("1. Connecting via psycopg2...")
conn = psycopg2.connect(direct_sync_url, connect_timeout=10)
conn.autocommit = True
cur = conn.cursor()

print("2. Terminating any open/idle connections...")
try:
    cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'neondb' AND pid <> pg_backend_pid();")
except Exception as e:
    print("Notice on terminate:", e)

print("3. Dropping and creating public schema...")
cur.execute("DROP SCHEMA public CASCADE;")
cur.execute("CREATE SCHEMA public;")
cur.execute("GRANT ALL ON SCHEMA public TO neondb_owner;")
cur.execute("GRANT ALL ON SCHEMA public TO public;")
cur.close()
conn.close()

print("4. Creating all tables from SQLAlchemy Base.metadata with engine...")
engine = create_engine(direct_sync_url, isolation_level="AUTOCOMMIT")
Base.metadata.create_all(bind=engine)

with engine.connect() as conn:
    print("5. Initializing alembic_version table...")
    conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(255) NOT NULL PRIMARY KEY);"))
    conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0008_complaint_ownership_details');"))

    print("6. Seeding Super Administrator...")
    super_role_id = str(uuid.uuid4())
    conn.execute(text("INSERT INTO roles (id, name, code, is_system, description) VALUES (:id, :name, :code, :is_sys, :desc)"), {
        "id": super_role_id, "name": "Super Administrator", "code": "SUPER_ADMIN", "is_sys": True, "desc": "Full unrestricted access."
    })
    
    super_user_id = str(uuid.uuid4())
    p_hash = get_password_hash("SuperSecureAdminPassword123!")
    conn.execute(text("""
        INSERT INTO users (
            id, email, phone, password_hash, first_name, last_name, ward,
            is_active, is_verified, is_superuser, mfa_enabled, failed_login_attempts
        ) VALUES (
            :id, :email, :phone, :hash, :fn, :ln, :ward, :act, :ver, :sup, :mfa, :fla
        )
    """), {
        "id": super_user_id,
        "email": "superadmin@electwin.com",
        "phone": "+91 98290 14285",
        "hash": p_hash,
        "fn": "Super",
        "ln": "Administrator",
        "ward": "All Wards",
        "act": True,
        "ver": True,
        "sup": True,
        "mfa": False,
        "fla": 0,
    })
    
    conn.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES (:u_id, :r_id)"), {
        "u_id": super_user_id, "r_id": super_role_id
    })

print("7. Verifying tables in database...")
with engine.connect() as conn:
    res = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"))
    tbls = [r[0] for r in res.fetchall()]
    print(f"SUCCESS! {len(tbls)} tables created in Neon DB:")
    print(tbls)

print("ALL DONE! Neon database is 100% created, verified and seeded!")
