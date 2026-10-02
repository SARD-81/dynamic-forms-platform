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

- [GATE 4 Production Readiness Execution Plan](project-control/gate4-execution-plan.md)
- [Project Gate Status](project-control/gate-status.md)
- [CHG-0007 — Gate 4 Team Lead Verification Governance](project-control/change-records/CHG-0007.md)
- [GATE 3 Application Execution Plan](project-control/gate3-execution-plan.md) — frozen historical execution record
- [Gate 3 Acceptance Verification](testing/gate3-acceptance-verification.md) — frozen acceptance evidence

## Authoritative active baselines entering Gate 4

- [BL-ARCH-002](project-control/baselines/BL-ARCH-002.md) — architecture
- [BL-DATA-002](project-control/baselines/BL-DATA-002.md) — domain/data
- [BL-FOUNDATION-002](project-control/baselines/BL-FOUNDATION-002.md) — active frozen Gate 3 engineering/runtime foundation until explicitly superseded
- [BL-APPLICATION-001](project-control/baselines/BL-APPLICATION-001.md) — frozen mandatory Gate 3 application behavior

`BL-FOUNDATION-001` remains frozen historical Gate 2 evidence and is not rewritten.

Gate 4 production-runtime changes require #78 / CHG-0006 before implementation is merged. Applied/verified Gate 4 runtime is expected to be captured later by a superseding `BL-FOUNDATION-003`, while release acceptance is expected to be captured by `BL-RELEASE-001`.

## Current Gate 4 state

- #79 production preflight — completed through PR #88;
- #80 health/readiness/logging — Draft PR #87, blocked from merge until #78 / CHG-0006;
- #89 / CHG-0007 — governance transition;
- #78 / CHG-0006 — next mandatory production-runtime authorization;
- #41 — optional real-time reporting bonus.

## Primary foundation documents

- [Environment contract](deployment/environment-contract.md)
- [Docker development](deployment/docker-development.md)
- [CI and branch governance](deployment/ci-and-branch-governance.md)
- [Foundation bootstrap verification](deployment/foundation-bootstrap-verification.md)
- [Quality and test foundation](testing/quality-test-foundation.md)
- [Shared presentation template contract](architecture/presentation-template-contract.md)
- [Authentication and email OTP contract](architecture/authentication-otp-contract.md)
- [Rendered ERD](database/erd.svg)
- [Authoritative ERD source](database/erd.nomnoml)

## Change-control rule

Frozen files are historical engineering records. Never rewrite a frozen baseline to hide a later decision. Record the change and supersede the baseline when required.
