# Granular RBAC Matrix & Role Hierarchies

## 1. Role Definitions

### 1. `SUPER_ADMIN`
Platform-level administrator with global privileges across all tenant organizations.
- Manages tenant organizations and billing tier activations.
- Creates and manages platform admins.
- Inspects system-wide audit logs and security events.
- Configures global communication gateways and system settings.

### 2. `ADMIN`
Organization and election-level administrator.
- Manages elections, positions, candidates, and polling stations within their assigned organization.
- Manages voter registry, bulk imports, and deduplication.
- Assigns volunteers to polling stations and shifts.
- Launches notification broadcast campaigns (WhatsApp, SMS, Instagram).
- Triggers vote counting, reviews reconciliations, and publishes certified results.
- **Perimeter Boundary**: Cannot access data belonging to other organizations.

### 3. `VOLUNTEER`
Restricted field operator.
- Operates strictly within assigned polling station and ward.
- Performs voter search, identity verification, and check-in.
- Reports station issues and views operational tasks.
- **Prohibitions**: Cannot edit election parameters, delete voter records, view confidential ballots, or export databases.

---

## 2. Granular Permissions Mapping

| Permission Code | Module | SUPER_ADMIN | ADMIN | VOLUNTEER |
| :--- | :--- | :---: | :---: | :---: |
| `system.manage` | System | Yes | No | No |
| `organization.create` | Org | Yes | No | No |
| `organization.view` | Org | Yes | Yes (Own) | No |
| `organization.update` | Org | Yes | Yes (Own) | No |
| `organization.suspend` | Org | Yes | No | No |
| `user.create` | User | Yes | Yes (Org) | No |
| `user.view` | User | Yes | Yes (Org) | No |
| `user.update` | User | Yes | Yes (Org) | No |
| `user.suspend` | User | Yes | Yes (Org) | No |
| `role.manage` | User | Yes | No | No |
| `permission.manage` | User | Yes | No | No |
| `election.create` | Election | Yes | Yes | No |
| `election.view` | Election | Yes | Yes | Yes (Assigned) |
| `election.update` | Election | Yes | Yes | No |
| `election.publish` | Election | Yes | Yes | No |
| `election.close` | Election | Yes | Yes | No |
| `election.cancel` | Election | Yes | Yes | No |
| `position.manage` | Election | Yes | Yes | No |
| `constituency.manage`| Election | Yes | Yes | No |
| `candidate.create` | Candidate | Yes | Yes | No |
| `candidate.view` | Candidate | Yes | Yes | Yes |
| `candidate.update` | Candidate | Yes | Yes | No |
| `candidate.approve` | Candidate | Yes | Yes | No |
| `candidate.reject` | Candidate | Yes | Yes | No |
| `voter.create` | Voter | Yes | Yes | Yes (Station) |
| `voter.view` | Voter | Yes | Yes | Yes (Station) |
| `voter.update` | Voter | Yes | Yes | No |
| `voter.import` | Voter | Yes | Yes | No |
| `voter.verify` | Voter | Yes | Yes | Yes (Station) |
| `voter.checkin` | Voter | Yes | Yes | Yes (Station) |
| `voter.block` | Voter | Yes | Yes | No |
| `station.manage` | Polling | Yes | Yes | No |
| `station.view` | Polling | Yes | Yes | Yes |
| `volunteer.assign` | Polling | Yes | Yes | No |
| `volunteer.view` | Polling | Yes | Yes | Yes |
| `result.view` | Results | Yes | Yes | No (Until Pub) |
| `result.count` | Results | Yes | Yes | No |
| `result.approve` | Results | Yes | Yes | No |
| `result.publish` | Results | Yes | Yes | No |
| `notification.send` | Messaging | Yes | Yes | No |
| `notification.manage`| Messaging | Yes | Yes | No |
| `notification.view` | Messaging | Yes | Yes | No |
| `dashboard.view` | Analytics | Yes | Yes | Yes |
| `report.generate` | Analytics | Yes | Yes | No |
| `audit.view` | Audit | Yes | Yes (Own) | No |
| `security.view` | Security | Yes | Yes (Own) | No |
