# Voting & Election Management System — Enterprise Backend

A production-grade, secure, modular, and scalable multi-tenant Voting and Election Management System backend built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.x**, **Alembic**, **Redis**, **Celery**, and **Pydantic v2**.

---

## Key Feature Highlights

- **Multi-Tenant Hierarchy**: `Organization -> Users -> Elections -> Voters -> Candidates -> Polling Stations -> Volunteers -> Results -> Notifications`.
- **Granular RBAC Engine**: Role definitions (`SUPER_ADMIN`, `ADMIN`, `VOLUNTEER`) with granular permission verification (`election.create`, `voter.checkin`, `result.publish`, etc.).
- **Security & Authentication**:
  - Argon2id password hashing with bcrypt fallback.
  - Short-lived JWT access tokens + cryptographically hashed refresh token rotation.
  - Multi-Factor Authentication (TOTP) with PyOTP and backup recovery codes.
  - Brute-force account lockout tracking.
  - Request correlation ID injection (`X-Request-ID`) and enterprise security headers.
  - Redis token-bucket rate limiting.
- **Strict Election Lifecycle State Machine**:
  - `DRAFT -> SCHEDULED -> UPCOMING -> LIVE -> PAUSED -> CLOSED -> COUNTING -> RESULT_PUBLISHED -> ARCHIVED`.
- **Anonymous Electronic Voting Engine**:
  - Strict constitutional ballot secrecy (no voter ID linked to cast ballot).
  - Double-voting prevention using transactional row-level locking (`SELECT FOR UPDATE`).
  - Cryptographic HMAC-SHA256 ballot receipt generation.
- **Bulk Voter Import Engine**:
  - CSV and Excel parsing with schema validation.
  - Duplicate voter detection across spreadsheets and database.
  - Validation preview generation and batch insertion with detailed error reporting.
- **Unified Notification System**:
  - Abstract adapter architecture supporting **SMS** (Twilio/AWS SNS), **WhatsApp Business Cloud API**, and **Instagram Direct Messaging**.
  - Jinja2 template rendering with variable schema validation.
  - Targeted voter cohort broadcast campaigns with delivery status tracking.
  - Provider webhook endpoints with HMAC-SHA256 signature verification.
- **Real-Time Dashboards & Analytics**:
  - Dedicated operational metrics for SuperAdmin, Admin, and Field Volunteer portals.
  - Turnout percentages, hourly trend curves, and station breakdowns.
- **Compliance & Auditing**:
  - Immutable, append-only operational audit logging.
  - Security incident and intrusion anomaly detection.

---

## Directory Structure

```
backend/
├── alembic/              # Database migration scripts
├── alembic.ini           # Alembic configuration
├── app/
│   ├── adapters/         # SMS, WhatsApp, Instagram, and Storage adapters
│   ├── api/v1/           # Modular REST API endpoints and router
│   ├── core/             # Config, security, database, permissions, middlewares, audit
│   ├── models/           # 33+ Normalized SQLAlchemy 2.0 entities
│   ├── repositories/     # Generic and domain data access repositories
│   ├── schemas/          # Pydantic v2 request/response validation schemas
│   ├── services/         # Business logic, state machines, and voting engine
│   ├── workers/          # Celery worker configuration and async tasks
│   └── main.py           # Application entry point and lifespan handlers
├── docs/                 # Architecture, ERD, API specs, RBAC, and Deployment docs
├── tests/                # Unit, integration, and security test suites
├── Dockerfile            # Multi-stage production container definition
├── docker-compose.yml    # Orchestration for FastAPI, PostgreSQL, Redis, Celery
└── requirements.txt      # Python dependencies
```

---

## Quickstart & Local Setup

### 1. Setup Virtual Environment
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configuration
```bash
cp .env.example .env
# Edit .env for your database, Redis, and secret keys
```

### Broadcast provider credentials

Broadcast groups route each voter independently using the saved WhatsApp/SMS channel. To send real messages, configure these values in `.env`:

- `TWILIO_ACCOUNT_SID`: Twilio Account SID.
- `TWILIO_AUTH_TOKEN`: Twilio Auth Token.
- `TWILIO_FROM_NUMBER`: approved SMS sender number in E.164 format, for example `+14155550100`.
- `TWILIO_WHATSAPP_FROM_NUMBER`: approved WhatsApp-enabled Twilio sender number in E.164 format, without the `whatsapp:` prefix.
- Set `SMS_PROVIDER=twilio` and `WHATSAPP_PROVIDER=twilio` to use Twilio for both channels.

Do not put credentials in source control. The default `mock` providers are for local development only and do not deliver messages to phones. The group send response and `broadcast_logs` always report each provider attempt, including failures.

### 3. Run Migrations & Start Server
```bash
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Interactive API Documentation
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Running the Automated Test Suite

```bash
pytest tests/ -v --cov=app
```
