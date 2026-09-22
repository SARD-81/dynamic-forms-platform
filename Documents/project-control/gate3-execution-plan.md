# GATE 3 — Application Feature Implementation Execution Plan

**Status:** IN PROGRESS  
**Tracker:** GitHub Issue #25  
**Integration branch:** `dev`  
**Applies after:** BL-ARCH-002, BL-DATA-002, BL-FOUNDATION-001

## Objective

Deliver the complete mandatory application feature set for the Dynamic Forms Platform while preserving the frozen architecture, data model, and engineering foundation.

Gate 3 is executed through small Issue-linked branches and reviewed Pull Requests to `dev`. No long-lived feature branch is used.

## Source requirement coverage

The Gate covers:

- Django authentication and OTP
- category management
- dynamic Forms with Text, Select, Checkbox, and frozen Number support
- public/private Forms with password protection
- unique participant links
- Form submissions and response browsing
- Processes made from existing Forms
- LINEAR and FREE Process execution
- public/private Processes
- Form and Process reports
- visit and response/completion counts
- weekly/monthly site-admin reports
- Email/API scheduled delivery
- Django REST Framework
- API documentation
- caching
- automated tests
- existing Docker/environment engineering contract

Real-time reporting is treated as a bonus/stretch item and is not a mandatory Gate 3 exit criterion.

## Team ownership

### SARD-81 — Team Lead / Cross-cutting integration

| Issue | Responsibility |
|---|---|
| #26 | Authentication + email OTP activation |
| #27 | Shared Django Template/UI shell |
| #32 | Public/private access, unique links, view count, Redis cache |
| #39 | CHG-0003 runtime-extension governance |
| #41 | BONUS real-time reporting |
| #42 | Final integration, baseline, Gate closure and milestone promotion |

### Mahsa-Alipour — Forms / Data-heavy domain

| Issue | Responsibility |
|---|---|
| #29 | Category management |
| #30 | Form lifecycle / ownership / visibility |
| #31 | Dynamic Question/QuestionOption builder |
| #33 | Transactional Form submissions and answers |
| #36 | Form reports / aggregation / response browsing |

### amirrezaparvaneh — API / Processes / Scheduled reporting

| Issue | Responsibility |
|---|---|
| #28 | API v1 + OpenAPI/Swagger foundation |
| #34 | Process lifecycle / visibility / step builder |
| #35 | LINEAR/FREE Process execution and resume |
| #37 | Process reports |
| #38 | ReportSubscription + report payload generation |
| #40 | Celery/Beat scheduled Email/API delivery |

## Execution waves

### Wave 1 — Foundations that can start immediately

- #26 — Auth/OTP — SARD-81
- #27 — shared template shell — SARD-81
- #28 — API/OpenAPI foundation — amirrezaparvaneh
- #29 — Categories — Mahsa-Alipour
- #39 — CHG-0003 — SARD-81

### Wave 2 — Authoring domains

- #30 — Form lifecycle — after #29
- #31 — Dynamic builder — after #30
- #34 — Process definition — after Form lifecycle is usable

### Wave 3 — Participant execution

- #32 — shared participant access/cache — after #30 and #34
- #33 — Form submission engine — after #31 and integration foundations
- #35 — Process execution — after #33, #34, and #32

### Wave 4 — Reporting and scheduled delivery

- #36 — Form reports — after #33/#32
- #37 — Process reports — after #35/#32
- #38 — periodic report subscription/payload — after reporting selectors exist
- #40 — Celery/Beat delivery — after #38 and approved #39

### Bonus

- #41 — real-time reporting — after #36/#37/#39

### Wave 5 — Gate closure

- #42 — final integration/regression/docs/application baseline and `dev → main` promotion

## Dependency graph

```text
#29
 ↓
#30
 ↓
#31
 ↓
#33 ─────────→ #36 ───────┐
                           ├→ #38 → #40
#34 → #32 → #35 → #37 ───┘
      ↑
 #30 ┘

#26 ─┐
#27 ─┼→ shared application integration
#28 ─┘

#39 ─→ #40
  └──→ #41 (BONUS)

Mandatory work → #42 → GATE 3 CLOSED → dev → main
```

## Architecture rules

All Issues must preserve the following:

1. write flow: presentation/API → Service → ORM;
2. reusable read flow: presentation/API → Selector → ORM;
3. transaction boundaries belong in Services;
4. post-commit side effects use `transaction.on_commit(...)`;
5. Forms must never import Processes;
6. frozen cross-table Service-only invariants require explicit tests;
7. environment variables are read only by settings/configuration;
8. Redis is accessed through Django/Celery/Channels abstractions, not ad-hoc clients;
9. model/schema changes require migration review and must not silently violate BL-DATA-002;
10. frozen foundation changes require a Change Record.

## Shared Definition of Done

A feature Issue is Done only when:

- stated acceptance criteria are implemented;
- success and important failure paths are tested;
- Service/Selector boundaries are respected;
- HTML and/or REST surface required by the Issue works;
- permission/ownership cases are tested;
- no secrets are committed;
- `ruff format --check .` passes;
- `ruff check .` passes;
- `pytest` passes;
- `python src/manage.py makemigrations --check --dry-run` passes;
- docs are updated when behavior/contracts change;
- PR targets `dev`;
- CI is green;
- peer review is complete.

## Gate 3 exit criteria

Gate 3 may close only when:

- all mandatory Issues #26–#40 are completed and merged;
- Issue #42 end-to-end scenarios pass;
- OpenAPI matches implemented REST endpoints;
- cache behavior and invalidation are verified;
- all frozen Service-only invariants have tests;
- scheduled Email/API reporting works;
- Docker development bootstrap remains valid;
- full regression suite and CI are green;
- application documentation is synchronized;
- `BL-APPLICATION-001` is reviewed/frozen;
- Gate status is updated to CLOSED;
- milestone PR `dev → main` is reviewed, green, and merged.

Issue #41 may be either completed or explicitly deferred as a bonus without blocking Gate closure.

## Coordination rules

- Start a dependent Issue only after its prerequisite is merged unless the isolated work cannot conflict.
- Coordinate before parallel edits to shared files such as settings, root URLs, base templates, Compose, or shared API configuration.
- If blocked for roughly one hour, report the blocker before changing architecture or duplicating another person's work.
- Rebase/merge latest `dev` before final verification of a long-running branch.
- Keep PRs scoped to their Issue; unrelated cleanup belongs in a separate Issue.
