# Gate 3 Acceptance Verification — Closure Candidate

**Issue:** #42  
**Candidate branch:** `chore/issue-42-gate3-closure-candidate`  
**Candidate base:** `dev@255d95b2150c89a07819d8a772cdc7742910d0fe`  
**Status:** CLOSURE CANDIDATE — NOT FROZEN / NOT CLOSED

## Purpose

This document is the final integrated Gate 3 acceptance map. It records how each mandatory scenario is verified by executable tests or CI runtime checks without duplicating feature tests merely to create a new checklist.

The Gate is intentionally not marked CLOSED in this candidate. The exact post-merge `dev` SHA cannot be known before the closure-candidate PR is merged. The authoritative freeze therefore occurs in a follow-up documentation-only PR that creates `BL-FOUNDATION-002` and `BL-APPLICATION-001` from the real merged `dev` commit.

## Acceptance matrix

### Identity

Covered by `src/apps/accounts/tests/test_authentication.py` and account database-constraint tests:

- registration;
- email OTP verification;
- login/logout;
- inactive-user behavior;
- wrong credentials and OTP failure/attempt paths.

### Form authoring

Covered by category, Form service/API/view, question-builder service/API/view, and participant-access suites:

- create category;
- create/edit Form;
- TEXT / NUMBER / SELECT / CHECKBOX questions;
- option authoring and reorder;
- publish/close lifecycle;
- unique participant link;
- PUBLIC and PRIVATE access.

### Form response

Covered by `src/apps/forms/tests/test_participant_submissions.py` and submission-service tests:

- anonymous submission;
- authenticated submission;
- answer validation;
- required/type/option invariants;
- closed Form rejects new submissions.

### Process execution

Covered by process execution Service/API/HTML tests plus `test_gate3_hardening.py`:

- LINEAR ordered execution and locking;
- FREE execution with both steps initially AVAILABLE;
- FREE browser flow completing step 2 before step 1 and finishing successfully;
- anonymous resume using a raw token whose hash is authoritative on ProcessRun;
- authenticated run ownership/resume;
- PRIVATE closed-process existing-run unlock/resume;
- CLOSED Process blocks new runs;
- raw anonymous resume token never enters the URL;
- one-time token is removed from the temporary session payload after first presentation.

### Form and Process reports

Covered by Form/Process report selector, HTTP/API, cache, and response/run browsing tests:

- view/submission/run/completion metrics;
- question aggregation;
- response/run detail browsing;
- owner isolation;
- DRAFT report cache correctness and invalidation behavior.

### Scheduled reports

Covered by `src/apps/reports/tests/test_delivery.py` and periodic payload/service tests:

- WEEKLY/MONTHLY due rules;
- creation-aware due eligibility;
- inactive subscription exclusion;
- EMAIL success/failure;
- API POST success, timeout and non-2xx failure;
- bounded retry behavior;
- one failed subscription does not prevent others being dispatched;
- `last_sent_at` changes only after successful external delivery;
- deterministic API `Idempotency-Key` and documented at-least-once semantics;
- eager test execution and Beat task registration.

### REST / OpenAPI

`tests/test_api_foundation.py` verifies the API root, schema endpoint and Swagger UI. `tests/test_gate3_acceptance_contract.py` adds a final cross-domain assertion that the OpenAPI document contains mandatory account, category, Form, Process, reporting, participant Form and participant Process surfaces.

### Cache correctness

Cache behavior remains optimization-only and PostgreSQL remains authoritative.

Evidence includes:

- `tests/test_cache_settings.py`: deterministic local-memory cache in tests;
- `src/apps/core/tests/test_participant_access.py`: versioned resource keys, outage behavior and rate-limit safety;
- `src/apps/forms/tests/test_participant_access.py`: cache hit, explicit invalidation, close invalidation and database fallback;
- corresponding Process participant/report cache tests, including DRAFT cache regression coverage.

## Required CI gates

The closure-candidate PR must pass all four jobs:

1. `lint`
   - `ruff format --check .`
   - `ruff check .`
2. `test`
   - full `pytest` suite against PostgreSQL + Redis test services
3. `migration-check`
   - `python src/manage.py check`
   - `python src/manage.py makemigrations --check --dry-run`
   - `docker compose --env-file .env.example config --quiet`
4. `docker-smoke`
   - build the repository Docker image from a clean runner;
   - start `web`, `postgres`, `redis`, `celery-worker`, and `celery-beat`;
   - wait for the containerized Django API to become reachable;
   - verify all five services are running;
   - Celery `inspect ping` against the worker;
   - verify scheduled-report task registration;
   - smoke `/accounts/login/`, `/api/v1/`, and `/api/schema/?format=json`;
   - verify mandatory OpenAPI paths from the running container;
   - tear down containers and volumes even on failure.

## Runtime/change-control state

Applied Gate 3 runtime changes are bounded by approved Change Records:

- CHG-0003: Redis cache activation and mandatory Celery worker/Beat development runtime;
- CHG-0004: production email configuration contract;
- CHG-0005: Team Lead Verification merge governance.

The historical `BL-FOUNDATION-001` remains immutable. Because CHG-0003 explicitly requires a superseding foundation baseline after the mandatory runtime changes land, Gate closure will create `BL-FOUNDATION-002` rather than editing BL-FOUNDATION-001.

## Bonus state

Issue #41 real-time reporting through Channels/WebSockets is **deferred from Gate 3 closure**. It is bonus/stretch scope and remains open for possible later implementation. No mandatory feature relies on WebSockets for correctness.

## Known non-blocking boundaries

- production deployment/Nginx topology is outside Gate 3 scope;
- scheduled API delivery is intentionally at-least-once across process/database failure windows; receivers get a deterministic `Idempotency-Key` for period-level deduplication;
- real-time report refresh is deferred bonus scope; HTTP reports remain authoritative and complete.

## Closure sequence

1. Review this closure-candidate PR.
2. Required CI must be fully green.
3. Team Lead decides whether to merge the candidate to `dev`.
4. Read the resulting exact `dev` SHA.
5. Open a documentation-only freeze PR that:
   - creates `BL-FOUNDATION-002` from the applied runtime state;
   - creates `BL-APPLICATION-001` from the integrated application state;
   - records exact freeze commit and final CI evidence;
   - updates Gate status from IN PROGRESS to CLOSED;
   - records #41 as deferred bonus.
6. After that freeze PR is reviewed/merged, open `dev → main` milestone promotion PR.
7. Merge promotion only after its own green CI and explicit Team Lead authorization.

This two-stage close avoids putting a guessed or pre-merge SHA into an authoritative frozen baseline.
