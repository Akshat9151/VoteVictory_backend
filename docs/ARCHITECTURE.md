# System Architecture & Technical Specifications

## 1. High-Level Architectural Model
The Voting Management System Backend is designed around a **Modular Clean Layered Architecture** with strict isolation of concerns, multi-tenant perimeter controls, and transactional integrity guarantees.

```
+-------------------------------------------------------------------------------+
|                             CLIENT / FRONTEND                                 |
|  - Web Admin Dashboard                                                        |
|  - SuperAdmin Operations Portal                                               |
|  - Volunteer Field Mobile / PWA                                               |
|  - Voter Electronic Balloting Interface                                       |
+-------------------------------------------------------------------------------+
                                      |
                                      | REST / JSON APIs (Bearer JWT, X-Request-ID)
                                      v
+-------------------------------------------------------------------------------+
|                      REVERSE PROXY & GATEWAY (Nginx)                          |
|  - TLS 1.3 Termination, CORS, Security Headers                                |
|  - IP Rate Limiting, DDoS Mitigations                                         |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
|                         FASTAPI ASYNC APPLICATION                             |
|                                                                               |
|  [ Middleware Pipeline ]                                                      |
|   ├── RequestCorrelationIdMiddleware (X-Request-ID propagation)               |
|   ├── SecurityHeadersMiddleware (HSTS, CSP, X-Frame-Options, Nosniff)         |
|   └── StructuredLoggingMiddleware (Latency, Path, Actor, IP, Status)          |
|                                                                               |
|  [ Security & Authorization Core ]                                            |
|   ├── JWT Access & Refresh Token Service (HMAC-SHA256 / RSA)                  |
|   ├── Argon2id Password Hashing Engine                                        |
|   ├── PyOTP Multi-Factor Authentication (TOTP)                                |
|   ├── Tenant Scope Resolver Dependency                                        |
|   └── Granular RBAC Dependency (User -> UserRole -> Role -> Permission)      |
|                                                                               |
|  [ API Router Layer (/api/v1) ]                                               |
|   ├── /auth, /users, /roles, /permissions, /organizations                     |
|   ├── /elections, /positions, /constituencies, /candidates                    |
|   ├── /voters, /imports, /polling-stations, /volunteers, /checkin             |
|   ├── /voting (Ballot issuance & anonymous casting)                           |
|   ├── /results (Counting, verification, approval, published locking)          |
|   ├── /notifications, /campaigns, /templates                                  |
|   └── /dashboard, /analytics, /audit, /webhooks, /health                      |
|                                                                               |
|  [ Service & Business Logic Layer ]                                           |
|   ├── ElectionLifecycleService (Strict State Machine)                         |
|   ├── VotingEngineService (Atomic Locking, Anonymous Vault, HMAC Receipts)    |
|   ├── BulkImportService (Schema check, Deduplication, Preview, Batch Insert)  |
|   ├── NotificationService (Unified Dispatcher & Template Engine)              |
|   └── DashboardAnalyticsService (Role-scoped Real-time Aggregations)          |
|                                                                               |
|  [ Notification Adapters ]                                                    |
|   ├── SMSProviderAdapter (Twilio / AWS SNS / Msg91)                           |
|   ├── WhatsAppProviderAdapter (Official Meta Cloud API v20.0+)                |
|   ├── InstagramProviderAdapter (Official Meta Graph API Direct Messages)      |
|   └── StorageAdapter (File Upload Validation & Secure Storage)                |
|                                                                               |
|  [ Repository & Data Access Layer ]                                           |
|   └── Generic BaseRepository[T] -> Domain Repositories (SQLAlchemy 2.0 Async) |
+-------------------------------------------------------------------------------+
                  |                                     |
                  v                                     v
+-----------------------------------+ +-----------------------------------------+
|     POSTGRESQL 16+ DATABASE       | |       REDIS 7+ CACHE & BROKER           |
|  - 33+ Relational Entity Tables   | |  - Token Blacklist & Session Storage    |
|  - Immutable Audit & Security Logs| |  - Rate Limiter Sliding Windows         |
|  - Anonymous Ballots & Choices    | |  - Celery Background Worker Task Queue  |
+-----------------------------------+ +-----------------------------------------+
```

## 2. Security Design & Defense in Depth
1. **Zero-Trust Multi-Tenancy**: Organization IDs supplied by frontend parameters are never trusted. All tenant filters derive from the authenticated JWT claims and user context.
2. **Granular RBAC**: Access control is enforced via granular permission strings (`election.create`, `voter.checkin`, `result.publish`) rather than hardcoded role strings.
3. **Password Security**: Argon2id password hashing prevents GPU/ASIC brute-force cracking.
4. **Token Security**: Short-lived JWT access tokens (15 minutes) paired with cryptographically hashed refresh tokens stored in database sessions with rotation on every refresh.
5. **Double-Voting Prevention**: Database `SELECT FOR UPDATE` transactional row locks, check constraints, and unique indexes guarantee that a voter can only cast a ballot once.
6. **Ballot Secrecy**: The anonymous ballot vault stores voter choices without referencing `voter_id`, ensuring voter privacy while returning a cryptographic HMAC SHA-256 receipt for audit verifiability.
