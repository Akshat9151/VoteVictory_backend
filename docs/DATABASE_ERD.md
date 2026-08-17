# Database Entity Relationship Design & Schema

## Relational Schema Diagram (Mermaid)

```mermaid
erDiagram
    ORGANIZATION ||--o{ USER : "has"
    ORGANIZATION ||--o{ ELECTION : "owns"
    ORGANIZATION ||--o{ VOTER : "registers"
    ORGANIZATION ||--o{ NOTIFICATION_CAMPAIGN : "runs"

    USER ||--o{ USER_ROLE : "has"
    ROLE ||--o{ USER_ROLE : "assigned_to"
    ROLE ||--o{ ROLE_PERMISSION : "contains"
    PERMISSION ||--o{ ROLE_PERMISSION : "granted_to"
    USER ||--o{ USER_SESSION : "maintains"

    ELECTION ||--|| ELECTION_SETTING : "configured_by"
    ELECTION ||--o{ CONSTITUENCY : "divides_into"
    ELECTION ||--o{ POSITION : "has"
    ELECTION ||--o{ CANDIDATE : "contested_by"
    ELECTION ||--o{ POLLING_STATION : "operates"
    ELECTION ||--o{ VOTER : "enrolls"
    ELECTION ||--o{ VOLUNTEER_ASSIGNMENT : "employs"
    ELECTION ||--o{ BALLOT : "vaults"
    ELECTION ||--o{ RESULT : "summarizes"

    POSITION ||--o{ CANDIDATE : "targets"
    CANDIDATE ||--o{ CANDIDATE_DOCUMENT : "verifies"
    POLLING_STATION ||--o{ VOLUNTEER_ASSIGNMENT : "staffed_by"
    POLLING_STATION ||--o{ VOTER_CHECKIN : "records"

    VOTER ||--o{ VOTER_VERIFICATION : "authenticates"
    VOTER ||--|| VOTER_CHECKIN : "checks_in"

    BALLOT ||--o{ VOTE : "contains"
    POSITION ||--o{ VOTE : "tallies"
    CANDIDATE ||--o{ VOTE : "receives"

    NOTIFICATION_TEMPLATE ||--o{ NOTIFICATION_CAMPAIGN : "formats"
    NOTIFICATION_CAMPAIGN ||--o{ NOTIFICATION_RECIPIENT : "dispatches"
    NOTIFICATION_RECIPIENT ||--o{ NOTIFICATION_DELIVERY : "logs"
```

## Key Entities & Field Descriptions

| Table Name | Primary Key | Key Relationships | Purpose |
| :--- | :--- | :--- | :--- |
| `organizations` | `id` (UUID) | One-to-many with users, elections, voters | Tenant isolation boundary |
| `users` | `id` (UUID) | FK `organization_id`, M2M with roles | User authentication & profiles |
| `roles` | `id` (UUID) | M2M with users and permissions | RBAC role definitions |
| `permissions` | `id` (UUID) | M2M with roles | Granular action strings |
| `elections` | `id` (UUID) | FK `organization_id` | Core election lifecycle entity |
| `positions` | `id` (UUID) | FK `election_id`, `constituency_id` | Electoral offices/posts |
| `candidates` | `id` (UUID) | FK `election_id`, `position_id` | Nominated candidates & profiles |
| `voters` | `id` (UUID) | FK `election_id`, `polling_station_id` | Electoral roll records |
| `voter_checkins` | `id` (UUID) | FK `voter_id`, `election_id` | Unique check-in timestamps |
| `ballots` | `id` (UUID) | FK `election_id` (NO voter reference!) | Anonymous encrypted ballot vault |
| `votes` | `id` (UUID) | FK `ballot_id`, `position_id`, `candidate_id` | Anonymous candidate selections |
| `results` | `id` (UUID) | FK `election_id`, `candidate_id` | Certified vote counts and ranks |
| `audit_logs` | `id` (UUID) | Append-only audit trail | Immutable compliance records |
| `security_events` | `id` (UUID) | Security incident records | Intrusion & anomaly monitoring |
