# Final project requirements and contract audit

**Reviewed:** 2026-10-02 UTC / 2026-10-03 Asia/Tehran  
**Purpose:** Team Lead-requested complete mandatory-scope re-audit before main promotion  
**Technical Freeze Point:** `f62cce74c67053ec2e2af06fb3ed75bd20a3ca00`  
**Audited candidate:** `241cc0f57f8e4a737a07f4384662ebb8c61dcb73`  
**Promotion evidence:** [PR #103](https://github.com/SARD-81/dynamic-forms-platform/pull/103), [#84](https://github.com/SARD-81/dynamic-forms-platform/issues/84), [#77](https://github.com/SARD-81/dynamic-forms-platform/issues/77)

## Sources, scope and result

The original five-page Persian project PDF was read as text and visually checked,
including requirements pages 3–5. The uploaded ERD was inspected against models,
real migrations, BL-DATA-002 and the constraint matrix. The bootcamp reference
provides educational context; the project PDF and approved repository contracts
are the feature acceptance authorities. Uploaded chat exports mostly concern an
earlier appointment project: their general Issue/PR/test/service/configuration
principles are relevant, but Doctor/Booking/Wallet requirements are not imported
into this project's scope.

All 294 candidate blobs were fetched or hash-verified against the exact live PR
HEAD in an independent snapshot. Code review covered models/constraints, Services,
Selectors, permission/session boundaries, participant execution, reporting/cache,
scheduled delivery, HTML/REST routes and production settings/topology/tooling.

**Result: no missing mandatory feature or confirmed merge-blocking defect was
found in this re-audit.** The status/authorization wording needed promotion
housekeeping so the published README would not keep claiming main merge was
prohibited or pending. This documentation update changes no implementation or
frozen baseline. Promotion still requires its own final green CI and review gate;
its actual merge SHA is recorded only after GitHub verifies it.

## Mandatory brief traceability

Paths below refer to the repository root. Each requirement has implementation
and regression coverage; this is not an inference from README claims alone.

| Original requirement | Implementation checked | Regression evidence |
| --- | --- | --- |
| Arbitrary Form/question counts | forms/services.py has no artificial quota; ordered Question/Option CRUD | forms/tests/test_question_builder_services.py, test_question_builder_api.py, test_question_builder_views.py |
| TEXT, SELECT and CHECKBOX | Question.QuestionType, type-specific configuration/answer validation, real HTML inputs; NUMBER also supported | forms/tests/test_submission_services.py, test_participant_submissions.py |
| Question-specific authoring data | TEXT max length; NUMBER bounds; SELECT/CHECKBOX options; required flag and order | forms/tests/test_question_builder_services.py, test_question_builder_api.py |
| Unique shareable Form link | Immutable UUID public_id; separate participant HTML/REST paths | forms/tests/test_participant_access.py |
| PUBLIC/PRIVATE Forms with password | Hashed secrets, object-scoped session grants, bounded fail-closed unlock | forms/tests/test_services.py, test_participant_access.py, test_participant_submissions.py |
| Process composed from existing Forms | ProcessStep ownership, unique Form/order, publication and row locks | processes/tests/test_services.py, test_api.py, test_views.py |
| PUBLIC/PRIVATE Processes | Publication/access checks, private process unlock and resume boundary | processes/tests/test_participant_access.py, test_participant_execution.py |
| LINEAR: no next step before current completion | AVAILABLE/LOCKED progression and atomic completion | processes/tests/test_execution_services.py, test_participant_execution.py, test_participant_execution_html.py |
| FREE: arbitrary step order | All steps AVAILABLE; completion requires every step | processes/tests/test_gate3_hardening.py, test_execution_services.py |
| User-managed categories | Owner-scoped CRUD and Form/Process category validation | core/tests/test_category_services.py, test_category_views.py, test_category_api.py |
| Numeric/choice aggregate report | Numeric min/max/sum/average; selection counts/denominators; empty-answer semantics | forms/tests/test_form_report_selectors.py, test_form_report_api.py, test_form_report_views.py |
| Form visits and response counts | Database F-expression views; authoritative submission revision; successful GET only | forms/tests/test_participant_access.py, test_form_report_selectors.py |
| Process visits and response counts | F-expression views; total/in-progress/completed runs and per-step distribution | processes/tests/test_participant_access.py, test_process_report_selectors.py, test_process_report_http.py |
| Browse received Form responses | Owner-scoped paginated list/detail, actual answer values, identity privacy | forms/tests/test_form_report_api.py, test_form_report_views.py |
| Weekly/monthly staff reports | Completed calendar periods, staff-controlled subscriptions/preview and due selection | reports/tests/test_services_and_payload.py, test_http.py |
| Email or specified API delivery | Django email plus bounded JSON POST, success-only last_sent_at, retry/isolation | reports/tests/test_delivery.py; real worker/Beat/task registration in both smoke jobs |
| Django REST Framework | Session-authenticated versioned domain APIs and separate public participant APIs | tests/test_api_foundation.py, tests/test_gate3_acceptance_contract.py, app API tests |
| Implemented API documentation | drf-spectacular schema/Swagger, mandatory owner/participant/report paths | tests/test_gate3_acceptance_contract.py, app schema tests, runtime OpenAPI smoke |
| Cache for speed | Django Redis cache, participant read models, revisioned reports; DB remains authoritative | core/tests/test_participant_access.py, Form/Process cache and reporting tests |
| Django authentication and OTP | Custom User, inactive registration, hashed expiring one-use OTP, cooldown/attempt limits, sessions | accounts/tests/test_authentication.py (HTML/API full flows and enforced-CSRF login) |
| Production settings/server/static | DEBUG=False, environment-owned settings, Daphne, deterministic migrate/collectstatic/preflight, collected assets | tests/test_production_security.py; actual production-smoke |
| Dockerization | Separate reproducible development/production images and Compose; no production source binds | preserved docker-smoke and production-smoke from clean runners |
| Environment-owned execution values | config.env/settings only; validated timeout/SMTP values; placeholders only | tests/test_settings_contract.py, test_cache_settings.py, test_production_email_settings.py |
| Automated tests | PostgreSQL-backed suite, focused failure/security tests and both topology jobs | 509 tests collected; full final-HEAD CI required before merge |
| Documents, ERD and startup README | Documents index, erd.svg/nomnoml, data dictionary/mapping, direct cross-platform startup/check/cleanup instructions | relative-link check and exact prior-baseline preservation |

Process-level response_count means completed ProcessRuns, explicitly accepted by
BL-APPLICATION-001 and the Process reporting contract. Partial runs are reported
separately; step Form submissions still appear in Form reports. CHECKBOX option
percentages need not sum to 100%, because one answer may select several options.

## Contract and security checks

- Modular monolith uses the approved five domain apps. Writes use Services and
  reads use Selectors. Owner reports are separate from participant access.
- No production Forms module imports Processes; shared integration checks use the
  approved core boundary. No business/domain module reads host environment values.
- All 21 named UniqueConstraint/CheckConstraint definitions were matched to real
  migration files. PostgreSQL constraint tests cover the executable DB authority.
- ProcessStepRun has UNIQUE(run, step), nullable OneToOne submission and state/data
  consistency. ProcessRun identity XOR/token uniqueness are DB-enforced. The four
  cross-table invariants remain validated in atomic Services with regression tests.
- Published schemas are immutable; close/delete behavior follows BL-DATA-002.
  Private secrets/anonymous resume digests are not exposed as owner report data.
  Anonymous resume tokens are disclosed once and kept out of participant URLs.
- Staff permissions protect scheduled subscription management and payload preview.
  External sends occur only through configured delivery paths; CI never contacts
  real SMTP/API recipients. At-least-once delivery with API idempotency metadata is
  an explicit accepted contract, not an exactly-once claim.
- Templates autoescape dynamic values; no raw safe/mark_safe/innerHTML/eval marker
  was found in the project's HTML/JavaScript. Shared controls and HTML regressions
  cover required inputs, ordering, errors, ownership and FREE execution.
- Production retains secure cookies and default HTTPS redirect. Nginx overwrites
  forwarded protocol; trusted HTTPS mode requires loopback ingress behind the
  operator TLS edge. Private/source files are denied; dependencies stay internal.
- Readiness uses disposable bounded DB/cache probes, safe generic failures and
  collision-free cache keys. Logs redact named credentials/tokens, parameterized
  messages, exception and stack text; raw query/access secrets are not logged.
- All eight existing baseline documents remain byte-for-byte unchanged by this
  promotion housekeeping. Technical/code acceptance remains at f62cce74; no new
  domain semantics, migration, dependency or BL-APPLICATION-002 is introduced.

## Repeated verification and evidence boundary

The independent snapshot passed Ruff lint/format and Django system checks under
all three settings modules: development, test and production. A focused local
configuration/security/timeout/health/verifier suite passed **129 tests**.
PostgreSQL and Docker are not installed in the Work terminal, so local results
are not represented as full database or topology evidence.

Full real PostgreSQL tests, migration drift and actual development/production
runtime acceptance are run on clean GitHub Actions runners. Before this re-audit,
PR #103 CI [37067664281](https://github.com/SARD-81/dynamic-forms-platform/actions/runs/37067664281)
had all five jobs SUCCESS with 509 tests; integrated Technical Freeze Point CI
[37066868098](https://github.com/SARD-81/dynamic-forms-platform/actions/runs/37066868098)
also passed. This documentation PR and the updated milestone each require a fresh
final-HEAD run; current run IDs/results and merge evidence are recorded in the
live PR/control records, rather than inventing future SHAs in this file.

Actual production-smoke covers deterministic init, migrations, preflight,
login/home/API/OpenAPI, health/static through Nginx, static replacement/removal on
retained volumes, internal healthy services, worker response/task registration,
Beat, separate DB/Redis outages, forged-protocol resistance and unconditional
container/volume cleanup. Bounded retries during intentional service recreation
are permitted; the final assertion must succeed within its finite deadline.

## Bonus scope and accepted non-blocking boundaries

Nginx is bonus wording in the PDF but is included as the team's approved Gate 4
production topology. Celery is an approved way to deliver mandatory periodic
reports. GraphQL, social login and WebSocket real-time refresh are not mandatory;
#41 remains explicitly deferred, with HTTP reporting authoritative.

A real deployment needs operator-owned TLS/certificates, actual secrets and
SMTP/API targets, backups and hosting. Native branch protection is unavailable
under the accepted private-repository plan; the explicit PR/CI/review gate still
applies. Neither limitation is a missing repository feature.

Private unlock throttling intentionally uses the trusted socket REMOTE_ADDR and
ignores client-supplied forwarding headers. Behind Nginx or a shared TLS edge,
visitors may share a conservative per-resource attempt budget. This is a
non-blocking availability/scaling boundary for the accepted bootcamp topology,
not an authentication bypass or a claim of per-end-user proxy-aware rate limiting.
Changing client-IP trust would need an explicit trusted-proxy contract and tests;
unverified headers are not enabled during promotion.

## Authorized promotion and closure

The owner's subsequent instruction explicitly authorizes this assistant to merge
PR #103 after the complete mandatory-scope audit, fixing confirmed blockers if
present, and final green verification. It supersedes the earlier instruction to
leave that milestone open; it does not authorize auto-merge or future main work.

Before merge: re-fetch current dev/main, require behind_by=0, clean intended delta,
all five checks completed SUCCESS on the captured HEAD, and no unresolved material
review. Squash merge with expected_head_sha; re-fetch and verify the resulting
main commit/tree. Only then close #84 and Tracker #77 completed and record the
actual promotion SHA/results. Existing frozen baseline files retain their original
activation-time history; later live promotion evidence does not rewrite them.
