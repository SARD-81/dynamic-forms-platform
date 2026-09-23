# Project Documentation

This directory is the version-controlled engineering record for the project.

## Structure

- `architecture/` — ADRs, architecture rationale, and shared presentation contracts
- `database/` — ERD source/render, data dictionary, model mapping, and constraint verification
- `project-control/` — gate status, execution plans, frozen baselines, decision log, and change records
- `deployment/` — environment, Docker, CI, bootstrap, and deployment records
- `testing/` — quality/test foundation
- `api/` — versioned API contracts and OpenAPI documentation

## Current execution

- [GATE 3 Application Execution Plan](project-control/gate3-execution-plan.md)
- [Project Gate Status](project-control/gate-status.md)

## Primary foundation documents

- [Environment contract](deployment/environment-contract.md)
- [Docker development](deployment/docker-development.md)
- [CI and branch governance](deployment/ci-and-branch-governance.md)
- [Foundation bootstrap verification](deployment/foundation-bootstrap-verification.md)
- [Quality and test foundation](testing/quality-test-foundation.md)
- [Shared presentation template contract](architecture/presentation-template-contract.md)
- [Rendered ERD](database/erd.svg)
- [Authoritative ERD source](database/erd.nomnoml)

## Change-control rule

Frozen files are historical engineering records. Never rewrite a frozen baseline to hide a later
decision. Record the change and supersede the baseline when required.
