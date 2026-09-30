# GATE 3 — Application Feature Implementation Execution Plan

**Status:** IN PROGRESS  
**Tracker:** GitHub Issue #25  
**Integration branch:** `dev`  
**Applies after:** BL-ARCH-002, BL-DATA-002, BL-FOUNDATION-001  
**Active governance extension:** CHG-0005 after its transition PR is merged

## Objective

Deliver the complete mandatory application feature set for the Dynamic Forms Platform while preserving the frozen architecture, data model, and engineering foundation.

Gate 3 uses small Issue-linked branches and Pull Requests to `dev`. No long-lived feature branch is used.

## Source requirement coverage

Gate 3 covers:

- Django authentication and OTP;
- categories;
- dynamic Forms with TEXT/NUMBER/SELECT/CHECKBOX questions;
- public/private Forms and Processes;
- unique participant links and view counting;
- Form submissions and response browsing;
- LINEAR and FREE Process execution/resume;
- Form and Process reporting;
- weekly/monthly admin reporting payloads/subscriptions;
- Email/API scheduled delivery;
- DRF/OpenAPI;
- caching;
- automated tests;
- existing Docker/environment engineering contract.

Real-time reporting through Channels/WebSockets is bonus/stretch scope and is not a mandatory Gate 3 exit criterion.

## Team ownership — current plan

### SARD-81 — Team Lead / heavy-feature / presentation / integration owner

Owns:

- #26 Authentication + email OTP activation;
- #27 shared Django Template/UI shell;
- #29 Categories;
- #30 Form lifecycle;
- #31 Dynamic Question/QuestionOption builder;
- #32 participant access/links/view count/cache;
- #33 transactional Form submissions;
- #35 all participant HTML/Template/browser execution/resume presentation and integration;
- #36 Form reporting;
- #37 complete Process reporting feature;
- #38 primary feature ownership: report payload/generation/integration, REST integration, admin HTML/UI/UX, E2E/tests/docs;
- #39 CHG-0003 runtime-extension governance;
- #41 BONUS real-time reporting;
- #42 final integration, regression, hardening, baselines, Gate closure, and milestone promotion;
- #47 CHG-0004 production email settings governance;
- #66 CHG-0005 Gate 3 merge-governance transition.

All remaining UI/UX, Django Template, HTML, CSS, browser rendering, and presentation-specific JavaScript belongs exclusively to SARD-81.

### amirrezaparvaneh — bounded backend/runtime lane

Owns or supports:

- #28 API v1 + OpenAPI foundation;
- #34 Process lifecycle/visibility/step backend;
- #35 Process execution Service/Selector/REST backend;
- #38 isolated ReportSubscription CRUD/validation/backend-permission support only;
- #40 Celery/Beat scheduled EMAIL/API delivery backend/runtime and backend tests.

No UI/UX, Django Template, HTML, CSS, or presentation-specific JavaScript is assigned to amirrezaparvaneh.

## Execution waves

### Completed foundation/application work

- #26, #27, #28, #29, #30, #31, #32, #33, #34, #35, #36, #37, #39 and #47 are implemented/merged.

### Remaining mandatory path

- #38 — ReportSubscription + delivery-neutral periodic report payload;
- #40 — Celery/Beat scheduled Email/API delivery;
- #42 — final integration/regression/hardening/docs/baselines and `dev → main` promotion.

### Parallelization

To minimize pending time:

- SARD-81 owns #38 integration-heavy work;
- amirrezaparvaneh may implement isolated #38 CRUD/validation backend support without touching presentation;
- after the #38 payload/delivery contract is stable, amirrezaparvaneh implements #40;
- while #40 is in progress, SARD-81 may advance #41 bonus work and #42 preparation where non-conflicting;
- final #42 closure waits for all mandatory #26–#40 work.

### Bonus

- #41 — real-time reporting after #36/#37/#39; may be completed or explicitly deferred without blocking Gate 3 closure.

## Dependency graph

```text
Forms path completed:
#29 → #30 → #31 → #33 → #36 ✅

Process path completed:
#34 → #32 → #35 → #37 ✅

Reporting/delivery remaining:
#36 + #37 → #38 → #40 → #42

#39 → #40
#47 → #40
#39 → #41 (BONUS)

Mandatory work → #42 → GATE 3 CLOSED → dev → main
```

## Architecture rules

All Issues must preserve:

1. write flow: presentation/API → Service → ORM;
2. reusable read flow: presentation/API → Selector → ORM;
3. transaction boundaries belong in Services;
4. post-commit side effects use `transaction.on_commit(...)`;
5. Forms must never import Processes;
6. frozen cross-table Service-only invariants require explicit tests;
7. environment variables are read only by settings/configuration;
8. Redis is accessed through Django/Celery/Channels abstractions, not ad-hoc clients;
9. model/schema changes require explicit migration review and must not silently violate BL-DATA-002;
10. frozen-foundation changes require a Change Record.

## Gate 3 Pull Request workflow — CHG-0005

After CHG-0005 becomes effective, the normal workflow is:

```text
Issue
→ short-lived branch from current dev
→ implementation + tests
→ PR to dev
→ required CI green
→ Team Lead Verification
→ squash merge to dev
```

Independent peer review is optional. It is not required for merge, Definition of Done, Issue closure, or Gate 3 closure.

No reviewer is automatically requested solely to satisfy governance.

### Team Lead Verification

Before merge, verify as applicable:

- PR scope matches its Issue/slice;
- branch is synchronized with current `dev` when final integration state matters;
- required CI is green;
- Ruff format/lint, pytest, Django system check, migration drift, and Docker/config checks pass where applicable;
- architecture/frozen-baseline boundaries remain intact;
- model/migration changes are explicitly intentional and reviewed when present;
- material automated/manual review findings are resolved or documented as accepted non-blocking limitations;
- security/privacy-sensitive paths have appropriate regression coverage;
- docs/contracts are synchronized;
- Team Lead explicitly authorizes merge.

## Shared Definition of Done

A feature Issue is Done only when:

- stated acceptance criteria are implemented;
- success and important failure paths are tested;
- Service/Selector boundaries are respected;
- required HTML and/or REST surfaces work;
- permission/ownership cases are tested;
- no secrets are committed;
- `ruff format --check .` passes;
- `ruff check .` passes;
- `pytest` passes;
- `python src/manage.py makemigrations --check --dry-run` passes;
- docs are updated when behavior/contracts change;
- PR targets `dev`;
- required CI is green;
- Team Lead Verification is complete and merge is explicitly authorized.

An independent peer `APPROVED` review is additional evidence when present, not a mandatory DoD item.

## Gate 3 exit criteria

Gate 3 may close only when:

- all mandatory Issues #26–#40 are completed and merged;
- Issue #42 end-to-end scenarios pass;
- OpenAPI matches implemented REST endpoints;
- cache behavior/invalidation is verified;
- all frozen Service-only invariants have tests;
- scheduled Email/API reporting works;
- Docker development bootstrap remains valid;
- applied CHG-0003 and CHG-0004 foundation changes are captured in a superseding foundation baseline;
- full regression suite and CI are green;
- application/developer/governance documentation is synchronized;
- `BL-APPLICATION-001` is verified and frozen;
- Gate status is updated to CLOSED;
- milestone PR `dev → main` is green, passes Team Lead Verification, is explicitly authorized, and is merged.

Issue #41 may be completed or explicitly deferred as a bonus without blocking Gate closure.

## Coordination rules

- Start dependent implementation only after prerequisites are merged unless work is demonstrably isolated/non-conflicting.
- Coordinate before parallel edits to shared settings, root URLs, base templates, Compose, or shared API configuration.
- Rebase/merge latest `dev` before final verification of a long-running branch when integration state has changed.
- Keep PRs scoped to their Issue; unrelated cleanup belongs separately.
- Do not auto-request reviewers merely to satisfy governance.
- Automated review tools may be used as verification input; material findings still require disposition before merge.
