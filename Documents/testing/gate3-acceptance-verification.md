# Gate 3 Acceptance Verification — Frozen Record

**Issue:** #42  
**Closure candidate:** PR #74  
**Technical freeze point:** `dev@72d5af1b5f26d9d3b8ba67605d96a69605878dcc`  
**Status:** VERIFIED / FROZEN

## Purpose

This document is the integrated Gate 3 acceptance map. It records how each mandatory scenario is verified by executable tests or CI runtime checks without duplicating feature tests merely to create a checklist.

PR #74 completed the final hardening and runtime verification and squash-merged to the exact technical freeze point above. The follow-up documentation-only freeze PR records that verified state in `BL-FOUNDATION-002` and `BL-APPLICATION-001`; it does not change application/runtime behavior.

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
- FREE execution with all steps initially AVAILABLE;
- FREE browser flow completing step 2 before step 1 and finishing successfully;
- anonymous resume using a raw token whose hash is authoritative on ProcessRun;
- authenticated run ownership/resume;
- PRIVATE closed-process existing-run unlock/resume;
- CLOSED Process blocks new runs;
- raw anonymous resume token never enters the URL;
- one-time token is removed from the temporary session payload after first presentation;
- an ambient authenticated session does not convert an anonymous run into an authenticated run.

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

`tests/test_api_foundation.py` verifies the API root, schema endpoint and Swagger UI.

`tests/test_gate3_acceptance_contract.py` verifies that the generated schema includes mandatory account, category, Form, Form-reporting, Process, Process-reporting, report-subscription, participant Form and participant Process surfaces.

The `docker-smoke` job repeats the mandatory-path assertion against the OpenAPI document served by the running containerized application. The final PR #74 review explicitly caught and fixed an initial mismatch where Form/Process reporting routes were missing from this runtime assertion.

### Cache correctness

Cache remains optimization-only and PostgreSQL remains authoritative.

Evidence includes:

- `tests/test_cache_settings.py`: deterministic test cache behavior;
- participant access suites: versioned keys, outage behavior, explicit invalidation and database fallback;
- Form and Process reporting cache regression coverage;
- DRAFT mutable-report cache safety.

## Final closure CI evidence

Final reviewed closure-candidate CI run: **#183**.

```text
lint                    SUCCESS
test                    SUCCESS — 365 passed
migration-check         SUCCESS
docker-smoke            SUCCESS
```

The successful `docker-smoke` job verified from a clean GitHub runner:

- repository image build;
- `web`, `postgres`, `redis`, `celery-worker`, `celery-beat` startup;
- Django readiness;
- all five services running;
- Celery worker `inspect ping`;
- scheduled-report dispatcher registration;
- login route;
- `/api/v1/`;
- runtime OpenAPI schema;
- all mandatory Gate 3 OpenAPI paths including Form and Process reporting;
- cleanup of containers and volumes.

## Runtime/change-control state

Applied Gate 3 runtime/configuration/governance changes are bounded by:

- CHG-0003: Redis cache activation and mandatory Celery worker/Beat development runtime; optional Channels part deferred;
- CHG-0004: production email configuration contract;
- CHG-0005: Team Lead Verification merge governance.

`BL-FOUNDATION-001` remains immutable historical evidence. `BL-FOUNDATION-002` freezes the actually applied active foundation at the technical freeze point.

## Bonus state

Issue #41 real-time reporting through Channels/WebSockets is **DEFERRED BONUS/STRETCH**.

It remains open for possible later implementation. No mandatory feature relies on WebSockets for correctness and HTTP reporting remains authoritative.

## Known non-blocking boundaries

- production deployment/Nginx topology is outside Gate 3 scope;
- scheduled API delivery is intentionally at-least-once across external/process failure windows; receivers get deterministic idempotency metadata;
- real-time report refresh is deferred bonus scope;
- Kubernetes, GraphQL and social login are outside Gate 3 scope.

## Freeze result

The verified technical state is frozen by:

- `BL-FOUNDATION-002` — engineering/runtime foundation;
- `BL-APPLICATION-001` — mandatory application behavior.

Both reference exact technical freeze commit:

`72d5af1b5f26d9d3b8ba67605d96a69605878dcc`

After the documentation-only freeze PR is reviewed and merged, Gate 3 is CLOSED/FROZEN on `dev` and the only remaining milestone control action is a separate Team Lead reviewed `dev → main` promotion PR.
