# Decision Log

## 2026-09-20 — ProcessRun respondent deletion policy

**Context:** GATE 2D implementation review.

**Decision:** `ProcessRun.respondent` uses `on_delete=PROTECT`.

**Reason:**

BL-DATA-002 freezes ProcessRun identity as exactly one of:

- authenticated: respondent present, resume-token digest absent;
- anonymous: respondent absent, resume-token digest present.

Using `SET_NULL` on an authenticated run would produce both identity fields as NULL and conflict with the frozen XOR database constraint. `PROTECT` preserves historical identity and makes deletion behavior explicit before the database constraint is reached.

**Change-control classification:** Documentation clarification only.

The currently committed BL-DATA-002 artifacts do not state a conflicting `SET_NULL` rule for this relation. Therefore this entry does not supersede BL-DATA-002 and does not require a CHG record.

If a future authoritative frozen baseline explicitly changes this policy, that change must use the normal CHG process.

## 2026-09-21 — Development integration branch and branch-protection availability

**Context:** GATE 2G CI and repository governance.

**Decision:** Normal ongoing development moves to a long-lived `dev` integration branch after
GATE 2G. `main` remains the stable milestone/release/baseline branch.

**Reason:** The project owner explicitly approved a `dev` integration workflow. Native GitHub branch
protection is unavailable for the current private repository under the active plan (HTTP 403), and
the repository will remain private.

**Change-control classification:** Structural governance change.

Tracked by CHG-0002 and frozen in BL-ARCH-002.
