# Project Documentation

This directory is the version-controlled engineering record for the project.

## Structure

- `architecture/` — ADRs and architecture rationale
- `database/` — ERD source/render, data dictionary, model mapping, and constraint verification
- `project-control/` — gate status, frozen baselines, decision log, and change records
- `deployment/` — environment, Docker, CI, bootstrap, and deployment records
- `testing/` — quality/test foundation
- `api/` — API documentation placeholder; concrete OpenAPI/API contracts arrive with API feature gates

## Primary foundation documents

- [Environment contract](deployment/environment-contract.md)
- [Docker development](deployment/docker-development.md)
- [CI and branch governance](deployment/ci-and-branch-governance.md)
- [Foundation bootstrap verification](deployment/foundation-bootstrap-verification.md)
- [Quality and test foundation](testing/quality-test-foundation.md)
- [Rendered ERD](database/erd.svg)
- [Authoritative ERD source](database/erd.nomnoml)

## Change-control rule

Frozen files are historical engineering records. Never rewrite a frozen baseline to hide a later
decision. Record the change and supersede the baseline when required.
