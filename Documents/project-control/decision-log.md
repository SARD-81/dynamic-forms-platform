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

## 2026-09-23 — Gate 3 runtime-extension baseline handling

**Context:** Issue #39 / CHG-0003.

**Decision:** Authorize bounded Gate 3 runtime extensions through CHG-0003 while keeping
BL-FOUNDATION-001 immutable as historical evidence.

A BL-FOUNDATION-002 is not frozen in Issue #39 because the runtime changes are not implemented or
verified by the change-control PR itself.

The superseding foundation baseline becomes required after the authorized mandatory runtime changes
are actually applied and verified, and before Gate 3 closes.

**Authorized implementation boundaries:**

- #32 may activate Django Redis cache through logical DB 0;
- #40 may add development Celery worker + Beat services using logical DB 1;
- #41 may add `channels-redis>=4.3.0,<4.4` and logical DB 2 only if the bonus feature is implemented.

**Reason:** Freezing a new foundation baseline before the implementation exists would turn a baseline
from verified evidence into a target-state specification. CHG-0003 provides the required approval
boundary without misrepresenting the current repository state.

**Change-control classification:** Structural engineering-foundation extension.

Tracked by CHG-0003. BL-FOUNDATION-001 is not edited in place.
