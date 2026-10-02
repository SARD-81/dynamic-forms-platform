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

## 2026-09-24 — Production email settings authorization boundary

**Context:** Issue #47 / CHG-0004, discovered during peer review of Issue #26.

**Decision:** Production SMTP configuration requires a dedicated settings/environment Change Record
before Issue #26 may add new mail transport variables.

CHG-0004 authorizes a vendor-neutral Django SMTP settings contract for #26 and later #40 while
keeping BL-FOUNDATION-001 immutable.

A BL-FOUNDATION-002 is not frozen by Issue #47. The already-required superseding foundation baseline
at Gate 3 closure must capture the actually applied email configuration.

**Reason:** BL-FOUNDATION-001 freezes the environment contract and CHG-0003 explicitly did not
authorize new production secrets. Adding SMTP host/user/password variables directly in #26 would
silently change the foundation contract.

**Change-control classification:** Structural settings/environment extension.

Tracked by CHG-0004.

## 2026-09-30 — Gate 3 Team Lead Verification replaces mandatory peer approval

**Context:** Issue #66 / CHG-0005, after repeated Gate 3 merges required Governance Exceptions solely because an independent peer `APPROVED` review was absent despite green CI and explicit Team Lead authorization.

**Decision:** For the remainder of Gate 3, independent peer review is optional rather than a mandatory merge/DoD gate. The required governance gate is **Team Lead Verification** backed by green CI, scope/architecture review, resolution or explicit acceptance of material findings, and explicit Team Lead merge authorization.

The same rule applies to the final `dev → main` Gate 3 milestone PR. Reviewers are not automatically requested merely to satisfy process.

Historical merges that occurred before CHG-0005 became effective remain classified according to the policy in force at their merge time; PR #63 and PR #65 therefore remain historical Governance Exceptions.

**Reason:** The small active team made mandatory peer approval a recurring process bottleneck and generated repetitive exception/audit work without changing the technical verification path. Team Lead Verification preserves explicit accountability while retaining CI, architecture, security, migration, documentation, and regression requirements.

**Change-control classification:** Structural repository-governance change for Gate 3 only.

Tracked by CHG-0005. No architecture, data, runtime, or settings baseline is changed.

## 2026-09-30 — Gate 3 technical freeze and baseline activation

**Context:** Issue #42 after closure-candidate PR #74 was reviewed, corrected and squash-merged.

**Decision:** Freeze the verified mandatory Gate 3 technical state at:

`dev@72d5af1b5f26d9d3b8ba67605d96a69605878dcc`

Two baselines record different aspects of the same verified state:

- `BL-FOUNDATION-002` supersedes BL-FOUNDATION-001 only for the active engineering/runtime foundation and captures the applied CHG-0003/CHG-0004 state plus active CI/runtime governance;
- `BL-APPLICATION-001` freezes mandatory Gate 3 application behavior and acceptance semantics.

BL-FOUNDATION-001 remains immutable historical Gate 2 evidence. BL-ARCH-002 and BL-DATA-002 remain authoritative architecture/data dependencies.

Issue #41 real-time Channels/WebSocket reporting is explicitly deferred as BONUS/STRETCH scope and does not block Gate 3 closure. HTTP reporting remains authoritative.

**Evidence:** PR #74 final CI #183 passed all four required jobs, including 365 tests and clean five-service Docker/OpenAPI smoke verification. The final runtime OpenAPI coverage finding was resolved before merge.

**Change-control classification:** Documentation-only baseline freeze / Gate closure. No application/runtime behavior is introduced by the freeze PR.

After the documentation-only freeze is merged to `dev`, the remaining milestone action is a separate `dev → main` PR with green required CI and Team Lead Verification.

## 2026-10-02 — Gate 4 Team Lead Verification governance

**Context:** Issue #92 / CHG-0007 during Gate 4 control-plane synchronization.

**Decision:** Gate 4 uses an explicit Team Lead Verification governance record rather than silently extending Gate 3-only CHG-0005. Independent peer `APPROVED` review is optional, reviewer requests are not required merely to satisfy process, and merge still requires green applicable CI, scope/architecture/security verification, disposition of material findings and an explicit Team Lead decision.

Automation/assistant work may prepare and verify PRs but does not merge Gate 4 PRs unless the repository owner gives an explicit per-merge override to the standing no-assistant-merge rule.

PR #88 / Issue #79 is retained as a historical Gate 4 Governance Exception because it merged before CHG-0007 became effective without the independent peer approval required by the initial Gate 4 plan. PR #85 is superseded because its kickoff branch became stale after #79 merged. Draft PR #86 must be refreshed/re-scoped or superseded. PR #87 remains merge-blocked until #78 / CHG-0006 authorizes its runtime/foundation boundary.

**Reason:** Gate 4 should preserve explicit Team Lead accountability and all technical verification controls without reintroducing reviewer-request churn that the repository owner explicitly rejected.

**Change-control classification:** Structural repository-governance change for Gate 4 only.

Tracked by CHG-0007. No frozen baseline, application behavior, runtime topology, model, migration or settings contract is changed by this governance record.
