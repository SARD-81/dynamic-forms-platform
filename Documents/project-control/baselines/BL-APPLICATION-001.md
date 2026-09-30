# BL-APPLICATION-001 — Gate 3 Application Feature Baseline

**Status:** FROZEN / AUTHORITATIVE  
**Approved:** 2026-09-30  
**Gate:** GATE 3 — Application Feature Implementation  
**Architecture dependency:** BL-ARCH-002  
**Data dependency:** BL-DATA-002  
**Foundation dependency:** BL-FOUNDATION-002  
**Technical freeze point:** `dev @ 72d5af1b5f26d9d3b8ba67605d96a69605878dcc`

## Decision

BL-APPLICATION-001 freezes the mandatory integrated application behavior delivered through Gate 3.

It records the repository state after the final closure-candidate hardening, acceptance verification and Docker/runtime smoke verification. The documentation-only freeze PR introduces no new feature behavior; it records the already verified technical state at the exact freeze point above.

## Mandatory application scope frozen

### Identity and authentication

- custom Django User model remains authoritative;
- registration creates inactive users pending email OTP activation;
- OTP verification activates the account;
- password/session login and logout are supported;
- invalid/inactive credential and OTP failure paths are enforced and tested.

### Categories

- authenticated owners can create/manage owner-scoped categories;
- category reads/writes remain owner-isolated.

### Dynamic Forms

- unlimited Forms;
- lifecycle: DRAFT → PUBLISHED → CLOSED;
- visibility: PUBLIC / PRIVATE;
- PRIVATE access requires the configured access secret through the participant-access flow;
- question types: TEXT, NUMBER, SELECT, CHECKBOX;
- question/option ordering and validation are enforced;
- schema is immutable after publish under the Gate 1 domain rules;
- unique participant links and view counting are implemented.

### Form submissions

- anonymous and authenticated submissions are supported;
- submission writes are transactional through Services;
- answer type/required/option/domain invariants are validated;
- closed Forms reject new responses;
- FormSubmission remains independent of Process ownership, as frozen by BL-DATA-002.

### Processes

- Process authoring composes Forms into ordered ProcessSteps;
- process types: LINEAR and FREE;
- visibility: PUBLIC / PRIVATE;
- new runs are allowed only for executable Processes;
- closed Processes reject new runs while valid existing-run resume semantics are preserved where allowed.

### Process execution semantics

LINEAR:

- first step AVAILABLE;
- later steps LOCKED;
- successful completion unlocks the next step;
- final step completion completes the ProcessRun.

FREE:

- all steps AVAILABLE from run start;
- participant may complete steps in arbitrary order;
- run completes only when all steps are complete.

Frozen Service-only execution invariants remain:

1. `ProcessStepRun.process_step.process_id == ProcessStepRun.process_run.process_id`;
2. `ProcessStepRun.submission.form_id == ProcessStepRun.process_step.form_id`;
3. `AnswerOption.option.question_id == Answer.question_id`;
4. `Answer.question.form_id == FormSubmission.form_id`.

### ProcessRun identity / resume

A ProcessRun has exactly one identity mode:

- authenticated: `respondent` present and resume-token hash absent;
- anonymous: `respondent` absent and resume-token hash present.

Anonymous raw resume tokens:

- are returned/presented only where needed for participant continuation;
- are never persisted as raw values;
- are never placed in participant URLs;
- may be held temporarily in browser session state until first presentation;
- are removed from that temporary session payload after first display;
- are compared using their stored digest/hash authority.

Ambient login does not convert an anonymous run into an authenticated run.

## Reporting

### Form reporting

Owner reporting includes:

- view count;
- submission count;
- response browsing;
- question-level aggregation;
- owner isolation;
- cache behavior that never replaces PostgreSQL as authority.

### Process reporting

Owner reporting includes:

- view count;
- total/in-progress/completed runs;
- completion rate;
- per-step status distribution;
- ProcessRun list/detail browsing;
- owner isolation;
- DRAFT-safe cache behavior.

## Scheduled reporting

Staff-managed ReportSubscription behavior includes:

- WEEKLY and MONTHLY frequencies;
- EMAIL and API delivery targets with the frozen XOR target constraint;
- deterministic completed reporting periods;
- privacy-safe delivery-neutral payload schema;
- due-subscription selection that respects creation time and last successful send;
- hourly Celery Beat due dispatch;
- EMAIL delivery through Django's configured email backend;
- JSON POST API delivery with finite timeout and 2xx-only success;
- bounded retry/backoff and per-subscription failure isolation;
- `last_sent_at` update only after successful delivery;
- deterministic period-level `Idempotency-Key` for API receivers;
- documented at-least-once delivery semantics across unavoidable external/process failure windows.

## API / OpenAPI

The application exposes versioned `/api/v1/` REST surfaces for the implemented mandatory domains and uses drf-spectacular for OpenAPI/Swagger documentation.

The Gate 3 acceptance contract verifies mandatory surfaces including:

- account login;
- categories;
- Forms;
- Form reporting;
- Processes;
- Process reporting;
- report subscriptions;
- public Form submissions;
- public Process runs.

OpenAPI runtime coverage is also verified inside the clean Docker smoke job.

## Presentation

The application includes Django Template/browser flows for:

- authentication and shared dashboard/navigation;
- category/Form/Process management;
- participant Form and Process execution;
- PRIVATE participant access;
- one-time anonymous resume-token presentation;
- Form/Process reporting;
- staff periodic-report subscription management and preview.

Gate 3 closure includes an HTML regression proving FREE Process completion in arbitrary order.

## Cache contract

Cache is an optimization only.

Frozen rules:

- PostgreSQL remains authoritative;
- cached participant/report reads have explicit invalidation/versioning behavior;
- DRAFT mutable-report state must not become stale authoritative state;
- cache outage must not corrupt domain data;
- credentials/raw secret tokens are not cached.

## Verification evidence

Closure-candidate PR #74 was reviewed, corrected for the final runtime OpenAPI coverage finding, and squash-merged to technical freeze commit:

`72d5af1b5f26d9d3b8ba67605d96a69605878dcc`

Final candidate CI run #183:

```text
lint                    PASS
pytest                   365/365 PASS
Django system check     PASS
migration drift check   PASS
Compose validation      PASS
docker-smoke            PASS
Celery verification     PASS
critical HTTP/API       PASS
runtime OpenAPI paths   PASS
```

The integrated acceptance mapping is recorded in `Documents/testing/gate3-acceptance-verification.md`.

## Mandatory Issue coverage

Gate 3 mandatory application/runtime implementation is represented by completed Issues:

- #26 authentication + email OTP;
- #27 shared presentation shell;
- #28 API/OpenAPI foundation;
- #29 categories;
- #30 Form lifecycle/visibility;
- #31 question builder;
- #32 participant access/cache;
- #33 Form submissions;
- #34 Process authoring;
- #35 Process execution/resume;
- #36 Form reporting;
- #37 Process reporting;
- #38 report subscriptions/payload;
- #40 scheduled delivery;
- #42 final integration/hardening/freeze.

Change-control Issues #39, #47 and #66 govern the runtime/email/governance extensions applied during Gate 3.

## Bonus / deferred state

Issue #41 — Channels/WebSockets real-time reporting — is not part of the mandatory Gate 3 acceptance baseline.

It is explicitly deferred as BONUS/STRETCH scope and remains eligible for later implementation under change control. HTTP reporting remains authoritative and complete.

## Known non-blocking boundaries

- production deployment and Nginx topology are outside Gate 3 scope;
- Kubernetes, GraphQL and social login are outside Gate 3 scope;
- scheduled API delivery is intentionally at-least-once; consumers receive deterministic idempotency metadata for deduplication;
- real-time report refresh is deferred bonus scope.

These boundaries do not block Gate 3 closure because they are outside mandatory scope or explicitly accepted semantics.

## Promotion rule

After this documentation-only freeze is reviewed and merged to `dev`, the Gate 3 integrated state is eligible for a separate `dev → main` milestone PR.

That milestone must pass the active required CI checks and Team Lead Verification before explicit Team Lead merge authorization.

Future application changes that alter frozen Gate 3 semantics require normal Issue/PR governance and, where they change frozen architecture/data/foundation decisions, the applicable Change Record/baseline process.

**GATE 3 APPLICATION FREEZE — COMPLETE**
