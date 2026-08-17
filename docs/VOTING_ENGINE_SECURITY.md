# Electronic Voting Engine & Cryptographic Integrity Architecture

## 1. Constitutional Ballot Secrecy Guarantee
In traditional paper ballots, once a voter places their marked ballot into the ballot box, their identity is irreversibly separated from their ballot choice.

The system mirrors this physical property digitally:
- The `voters` table maintains voter status: `has_voted = TRUE`, `voted_at = TIMESTAMP`.
- The `ballots` table records anonymous cast ballots: `id`, `election_id`, `constituency_id`, `ballot_serial_hash`, `cast_timestamp`, `is_valid`.
- The `votes` table references `ballot_id`, `position_id`, `candidate_id`.
- **Zero Queryable Link**: There is no foreign key or joinable relationship between `voters.id` and `ballots.id` or `votes.id`.

```
+------------------------------------+         +-------------------------------------+
|            VOTERS TABLE            |         |            BALLOTS TABLE            |
|  - id: voter_uuid                  |         |  - id: ballot_uuid                  |
|  - voter_id_number: "EPIC12345"    |         |  - election_id: elec_uuid           |
|  - has_voted: TRUE                 |         |  - ballot_serial_hash: HMAC-SHA256  |
|  - voted_at: 2026-08-17 14:05:00   |         |  - cast_timestamp: 2026-08-17...   |
+------------------------------------+         +-------------------------------------+
                  │                                               │
                  │  (SEPARATE DATABASE IDENTITIES)               │
                  ▼                                               ▼
         [ Voter Marked as Voted ]                      [ Anonymous Choices ]
                                                                  │
                                                                  ▼
                                                       +--------------------+
                                                       |    VOTES TABLE     |
                                                       | - ballot_id        |
                                                       | - position_id      |
                                                       | - candidate_id     |
                                                       +--------------------+
```

---

## 2. Multi-Tier Double-Voting Prevention

1. **Application-Level Validation**:
   - Verify `voter.has_voted == False` and `voter.voting_status != 'VOTED'`.
   - Verify that the election state is strictly `LIVE`.
2. **Ephemeral Session Invalidation**:
   - Voting sessions are short-lived (15 minutes).
   - Once a vote is cast, `session.status` is atomically transitioned from `ACTIVE` to `USED`.
3. **Transactional Database Row Locking (`SELECT FOR UPDATE`)**:
   - To defeat concurrent race condition attacks (e.g. submitting two simultaneous votes in parallel HTTP threads), the voter row is locked:
   ```sql
   SELECT id, has_voted FROM voters WHERE id = :voter_id FOR UPDATE;
   ```
4. **Unique Constraints & Atomicity**:
   - Check-in unique constraint: `UNIQUE(election_id, voter_id)`.
   - All mutations execute inside a single atomic database transaction. If any step fails, the entire transaction is rolled back.

---

## 3. Cryptographic Verifiability & HMAC Receipts
When a voter casts their ballot, the system generates a cryptographic receipt:
$$\text{ballot\_serial\_hash} = \text{HMAC-SHA256}(\text{SECRET\_KEY}, \text{election\_id} \mathbin{\Vert} \text{nonce})$$

The voter receives this receipt, allowing verification of ballot inclusion during audit reconciliation without revealing their candidate choices.
