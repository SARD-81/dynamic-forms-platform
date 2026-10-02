# Project Documentation

This directory is the version-controlled engineering record for the project.

## Structure

- `architecture/` — ADRs, architecture rationale, and shared presentation contracts
- `database/` — ERD source/render, data dictionary, model mapping, and constraint verification
- `project-control/` — gate status, execution plans, frozen baselines, decision log, and change records
- `deployment/` — environment, Docker, CI, bootstrap, and deployment records
- `testing/` — quality/test and integrated acceptance verification
- `api/` — versioned API contracts and OpenAPI documentation

## Current execution / control

- [GATE 4 Production Readiness Execution Plan](project-control/gate4-execution-plan.md) — **IN PROGRESS**
- [Project Gate Status](project-control/gate-status.md)
- [CHG-0007 Gate 4 Team Lead Verification Governance](project-control/change-records/CHG-0007.md) — proposed until transition PR merge
- [GATE 3 Application Execution Plan](project-control/gate3-execution-plan.md) — closed/frozen historical execution record
- [Gate 3 Acceptance Verification](testing/gate3-acceptance-verification.md)

Gate 3 is CLOSED / FROZEN and was promoted to `main` through milestone PR #76. Gate 4 now owns production readiness and release hardening tracked by GitHub Issue #77.

Current Gate 4 integration facts:

- #79 production preflight implementation is merged on `dev` through PR #88;
- #78 / CHG-0006 is the next mandatory production-runtime authorization;
- #80 PR #87 is open but runtime/foundation merge is blocked until CHG-0006 is effective;
- #81 production ASGI/Nginx/collectstatic work starts only after #78;
- #41 real-time reporting remains optional/non-blocking.

## Authoritative active baselines

- [BL-ARCH-002](project-control/baselines/BL-ARCH-002.md) — architecture
- [BL-DATA-002](project-control/baselines/BL-DATA-002.md) — domain/data
- [BL-FOUNDATION-002](project-control/baselines/BL-FOUNDATION-002.md) — active frozen Gate 3 engineering/runtime foundation until superseded through approved Gate 4 change control
- [BL-APPLICATION-001](project-control/baselines/BL-APPLICATION-001.md) — frozen mandatory Gate 3 application behavior

`BL-FOUNDATION-001` remains frozen historical Gate 2 evidence and is superseded only for the active foundation state; it is not rewritten.

Gate 4 proposes `BL-FOUNDATION-003` and `BL-RELEASE-001` only after the production runtime is actually implemented and verified. Production packaging alone does not create a new application semantic baseline.

## Primary foundation documents

- [Environment contract](deployment/environment-contract.md)
- [Docker development](deployment/docker-development.md)
- [CI and branch governance](deployment/ci-and-branch-governance.md)
- [Foundation bootstrap verification](deployment/foundation-bootstrap-verification.md)
- [Quality and test foundation](testing/quality-test-foundation.md)
- [Shared presentation template contract](architecture/presentation-template-contract.md)
- [Authentication and email OTP contract](architecture/authentication-otp-contract.md)
- [Periodic report contract](architecture/periodic-report-contract.md)
- [Form reporting contract](architecture/form-reporting-contract.md)
- [Process reporting contract](architecture/process-reporting-contract.md)
- [Participant access/cache contract](architecture/participant-access-cache-contract.md)
- [Rendered ERD](database/erd.svg)
- [Authoritative ERD source](database/erd.nomnoml)

## Change-control rule

Frozen files are historical engineering records. Never rewrite a frozen baseline to hide a later decision. Record the change and supersede the baseline when required.
