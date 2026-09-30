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

- [GATE 3 Application Execution Plan](project-control/gate3-execution-plan.md)
- [Project Gate Status](project-control/gate-status.md)
- [Gate 3 Acceptance Verification](testing/gate3-acceptance-verification.md)

## Authoritative active baselines

- [BL-ARCH-002](project-control/baselines/BL-ARCH-002.md) — architecture
- [BL-DATA-002](project-control/baselines/BL-DATA-002.md) — domain/data
- [BL-FOUNDATION-002](project-control/baselines/BL-FOUNDATION-002.md) — active engineering/runtime foundation after Gate 3
- [BL-APPLICATION-001](project-control/baselines/BL-APPLICATION-001.md) — frozen mandatory Gate 3 application behavior

`BL-FOUNDATION-001` remains frozen historical Gate 2 evidence and is superseded only for the active foundation state; it is not rewritten.

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

Frozen files are historical engineering records. Never rewrite a frozen baseline to hide a later
decision. Record the change and supersede the baseline when required.
