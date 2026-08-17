# REST API Specification (OpenAPI v1)

All API endpoints are prefixed with `/api/v1/`.

## Standard Response Format

### Success Response
```json
{
  "success": true,
  "message": "Operation completed successfully.",
  "data": { ... },
  "request_id": "c62b9f3d-8884-4b5b-86d1-4db8cfa8269d",
  "timestamp": "2026-08-17T18:00:00.000Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "DOUBLE_VOTING_PREVENTED",
    "message": "Double voting prevented. Voter has already cast a ballot.",
    "details": { "voter_id": "voter_123" }
  },
  "request_id": "c62b9f3d-8884-4b5b-86d1-4db8cfa8269d",
  "timestamp": "2026-08-17T18:00:00.000Z"
}
```

---

## Complete API Route Index

### 1. Authentication (`/api/v1/auth`)
- `POST /auth/login`: Authenticate with email/password & optional MFA.
- `POST /auth/refresh`: Rotate refresh token and issue new access token.
- `POST /auth/logout`: Revoke active session token.
- `POST /auth/mfa/setup`: Generate TOTP secret and provisioning URI.
- `POST /auth/mfa/confirm`: Activate MFA using verified 6-digit code.

### 2. User & Access Management (`/api/v1/users`)
- `GET /users/me`: Get current authenticated user profile and permissions.
- `GET /users/`: Paginated list of users in organization.
- `POST /users/`: Create a new user (Super Admin, Admin, Volunteer).
- `GET /users/{id}`: Fetch user details by ID.
- `PUT /users/{id}`: Update user profile and active status.
- `GET /users/roles/all`: List available roles and assigned permissions.
- `GET /users/permissions/all`: List all granular system permissions.

### 3. Organization Management (`/api/v1/organizations`)
- `GET /organizations/`: List tenant organizations.
- `POST /organizations/`: Provision a new tenant organization (Super Admin only).
- `GET /organizations/{id}`: Get organization details.
- `PUT /organizations/{id}`: Update organization configuration and status.

### 4. Election Management (`/api/v1/elections`)
- `GET /elections/`: List elections with status and type filters.
- `POST /elections/`: Create a new election draft.
- `GET /elections/{id}`: Get full election details, positions, and settings.
- `PUT /elections/{id}`: Update election dates, description, and visibility.
- `POST /elections/{id}/transition`: State machine lifecycle transitions (`DRAFT` -> `SCHEDULED` -> `LIVE` -> `CLOSED` -> `RESULT_PUBLISHED`).
- `PUT /elections/{id}/settings`: Configure voting rules, MFA requirements, and abstain options.

### 5. Positions & Constituencies (`/api/v1/positions`, `/api/v1/constituencies`)
- `GET /positions/election/{election_id}`: List positions for election.
- `POST /positions/`: Add an election position.
- `PUT /positions/{id}`: Update position limits and ordering.
- `GET /constituencies/election/{election_id}`: List election constituencies.
- `POST /constituencies/`: Create constituency / region.

### 6. Candidates (`/api/v1/candidates`)
- `GET /candidates/election/{election_id}`: List candidates with position/status filters.
- `POST /candidates/`: Register a new candidate nomination.
- `GET /candidates/{id}`: Get candidate profile and verified documents.
- `PUT /candidates/{id}`: Update candidate details and manifesto.
- `POST /candidates/{id}/status`: Approve, reject, or mark candidate as withdrawn.

### 7. Voters & Bulk Import (`/api/v1/voters`, `/api/v1/imports`)
- `GET /voters/election/{election_id}`: Filter, search, and paginate voters.
- `POST /voters/`: Enroll an individual voter.
- `GET /voters/{id}`: Get voter record.
- `PUT /voters/{id}`: Update voter address, ward, or contact info.
- `POST /voters/{id}/verify`: Verify voter identity (OTP, ID proof).
- `POST /imports/upload`: Upload CSV/Excel spreadsheet for validation preview.
- `POST /imports/confirm`: Confirm preview and execute bulk insert.

### 8. Polling Stations & Volunteers (`/api/v1/polling-stations`, `/api/v1/volunteers`)
- `GET /polling-stations/election/{election_id}`: List polling stations with turnout counts.
- `POST /polling-stations/`: Add a new polling station.
- `GET /volunteers/election/{election_id}`: List volunteer station assignments.
- `POST /volunteers/assign`: Assign volunteer to station and shift.

### 9. Check-in & Electronic Voting (`/api/v1/checkin`, `/api/v1/voting`)
- `POST /checkin/`: Verify voter identity and record polling station check-in.
- `POST /voting/auth-ballot`: Voter authentication, eligibility check, and ballot generation.
- `POST /voting/cast`: Atomic anonymous ballot casting with HMAC serial receipt.

### 10. Results Management (`/api/v1/results`)
- `GET /results/election/{election_id}`: View certified results and turnout.
- `POST /results/election/{election_id}/tally`: Trigger automatic ballot counting.
- `POST /results/publish`: Approve and officially lock published results.

### 11. Unified Notifications (`/api/v1/notifications`)
- `POST /notifications/send`: Send direct message via SMS, WhatsApp, or Instagram.
- `POST /notifications/campaigns`: Launch targeted broadcast campaign to voter cohorts.
- `GET /notifications/campaigns/{id}/report`: View real-time delivery logs.
- `GET /notifications/templates`: List approved message templates.
- `POST /notifications/templates`: Register new message template.

### 12. Dashboards & Analytics (`/api/v1/dashboard`, `/api/v1/analytics`)
- `GET /dashboard/superadmin`: Platform-wide stats, active elections, security events.
- `GET /dashboard/admin/{election_id}`: Turnout, voter stats, volunteer metrics.
- `GET /dashboard/volunteer`: Personal ward stats, assigned voters, check-in actions.
- `GET /analytics/election/{election_id}/turnout`: Hourly trends, station and ward breakdown.

### 13. Audit & Security (`/api/v1/audit`)
- `GET /audit/logs`: Immutable append-only audit trail.
- `GET /audit/security-events`: Real-time anomaly alerts (failed logins, double voting attempts).

### 14. Webhooks & Health (`/api/v1/webhooks`, `/api/v1/health`)
- `POST /webhooks/sms`: Twilio delivery webhook.
- `GET /webhooks/whatsapp`: Meta webhook subscription challenge.
- `POST /webhooks/whatsapp`: Meta WhatsApp status delivery webhook.
- `POST /webhooks/instagram`: Meta Instagram messaging webhook.
- `GET /health`, `GET /health/live`, `GET /health/ready`: System diagnostics probes.
