# GATE 3 — Application Feature Implementation Execution Plan

**Status:** CLOSURE CANDIDATE / IN PROGRESS  
**Tracker:** GitHub Issue #25  
**Integration branch:** `dev`  
**Current mandatory implementation base:** `255d95b2150c89a07819d8a772cdc7742910d0fe`  
**Applies after:** BL-ARCH-002, BL-DATA-002, BL-FOUNDATION-001  
**Active governance:** CHG-0005

## Objective

Deliver and verify the complete mandatory application feature set for the Dynamic Forms Platform while preserving the frozen architecture, data model, and historical baselines.

Gate 3 uses short-lived Issue-linked branches and Pull Requests to `dev`. No long-lived feature branch is used.

## Mandatory scope coverage

All mandatory implementation/runtime work through Issue #40 is merged to `dev`:

- #26 — authentication + email OTP activation;
- #27 — shared Django Template shell/navigation/dashboard;
- #28 — API v1 + OpenAPI/Swagger foundation;
- #29 — categories;
- #30 — Form lifecycle / visibility;
- #31 — dynamic question builder and options;
- #32 — participant access, unique links, view counting and Redis cache;
- #33 — transactional Form submissions and Answer validation;
- #34 — Process definition and step authoring;
- #35 — LINEAR/FREE Process execution + browser/API resume;
- #36 — Form analytics and response browsing;
- #37 — Process analytics and ProcessRun reporting;
- #38 — ReportSubscription management + WEEKLY/MONTHLY payload;
- #39 — CHG-0003 runtime-extension authorization;
- #40 — Celery/Beat scheduled EMAIL/API delivery;
- #47 — CHG-0004 production email configuration authorization;
- #66 — CHG-0005 Team Lead Verification governance transition.

## Current work — Issue #42

Issue #42 is the final mandatory Gate 3 closure path. It owns:

- integrated regression/hardening;
- final OpenAPI/cache/runtime verification;
- clean Docker bootstrap smoke verification;
- final documentation synchronization;
- application/runtime baseline freeze;
- Gate 3 closure;
- `dev → main` milestone promotion preparation.

### Closure-candidate phase

The first #42 PR must:

- add any missing final regression coverage;
- verify all mandatory acceptance scenarios through existing or new executable tests;
- add a clean five-service Docker smoke gate;
- synchronize README, Gate status and verification documentation;
- keep Gate 3 explicitly IN PROGRESS;
- not create a frozen baseline with a guessed pre-merge SHA.

### Freeze phase

After the closure-candidate is reviewed and merged by the Team Lead, read the exact resulting `dev` SHA and open a small documentation-only freeze PR that:

- creates `BL-FOUNDATION-002` for the applied CHG-0003/CHG-0004 runtime/configuration state;
- creates `BL-APPLICATION-001` for the verified Gate 3 application state;
- records final CI evidence and exact freeze commit;
- updates Gate status to CLOSED;
- records #41 as deferred bonus.

This two-stage approach is required because the repository uses squash merge and the authoritative post-merge `dev` SHA is not knowable before merge.

## Bonus scope

Issue #41 — real-time report refresh using Channels/WebSockets — is BONUS/STRETCH and is explicitly deferred from Gate 3 closure.

The Issue remains open for possible future implementation. HTTP reporting remains authoritative and no mandatory feature depends on WebSockets.

## Architecture rules

All Gate 3 work preserves:

1. write flow: presentation/API → Service → ORM;
2. reusable read flow: presentation/API → Selector → ORM;
3. transaction boundaries in Services;
4. transaction-dependent side effects through `transaction.on_commit(...)`;
5. Forms never importing Processes;
6. explicit tests for frozen Service-only invariants;
7. environment variables read only by settings/configuration;
8. Redis accessed only through Django/Celery/Channels framework abstractions;
9. explicit migration review for any model/schema change;
10. frozen historical baselines never edited in place.

## Runtime state after #40

The mandatory development topology is:

```text
web
postgres
redis
celery-worker
celery-beat
```

Redis logical separation remains:

```text
DB 0 → Django cache
DB 1 → Celery broker
DB 2 → Channels layer only if #41 is implemented later
```

Development scheduled reports use Django's console email backend. Production email configuration follows CHG-0004 and is not a production-deployment design.

## Pull Request workflow — CHG-0005

```text
Issue
→ short-lived branch from current dev
→ implementation + tests
→ PR to dev
→ required CI green
→ Team Lead Verification
→ explicit Team Lead merge decision
```

Independent peer review is optional. It is not required for merge, Definition of Done, Issue closure, or Gate 3 closure.

No reviewer is automatically requested solely to satisfy governance.

## Required CI gates

Gate 3 closure-candidate and milestone work must pass:

- `lint` — Ruff format and lint;
- `test` — full pytest suite;
- `migration-check` — Django system check, migration drift, Compose config;
- `docker-smoke` — clean build/start of all five development services, Celery worker/task verification, and critical HTML/API/OpenAPI smoke routes.

The detailed acceptance map is maintained in `Documents/testing/gate3-acceptance-verification.md`.

## Gate 3 exit criteria

Gate 3 may close only when:

- all mandatory Issues #26–#40 are merged;
- Issue #42 integrated acceptance scenarios pass;
- OpenAPI matches mandatory REST surfaces;
- cache correctness/invalidation and database fallback are verified;
- scheduled EMAIL/API reporting is verified;
- the full five-service Docker bootstrap smoke check passes;
- full regression suite, Ruff, Django check and migration drift are green;
- application/developer/governance documentation is synchronized;
- `BL-FOUNDATION-002` is frozen at the exact verified `dev` commit;
- `BL-APPLICATION-001` is frozen at the exact verified `dev` commit;
- Gate status is updated to CLOSED;
- Issue #41 is either completed or explicitly deferred as bonus;
- milestone PR `dev → main` passes its own CI and Team Lead Verification before merge.

## Promotion

After the freeze PR is merged and Gate 3 is CLOSED:

```text
dev
→ Pull Request to main
→ full CI including docker-smoke
→ Team Lead Verification
→ explicit Team Lead merge decision
```

Production deployment, Nginx topology, Kubernetes, GraphQL and social login remain outside Gate 3 scope.
