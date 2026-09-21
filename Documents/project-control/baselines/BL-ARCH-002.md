# BL-ARCH-002 — Application Architecture Baseline

**Status:** FROZEN  
**Approved:** 2026-09-21  
**Gate:** GATE 0 — Scope & Architecture  
**Gate status:** CLOSED  
**Supersedes:** BL-ARCH-001  
**Change record:** CHG-0002

## Architecture style

Modular Monolith.

## Frozen technology baseline

- Django
- Django REST Framework
- Django Channels
- Celery
- Celery Beat
- PostgreSQL
- Redis
- Django Templates
- Vanilla JavaScript
- Nginx
- Docker Compose
- OpenAPI / Swagger
- Ruff
- automated tests
- GitHub Actions

## Code organization

- domain-oriented Django apps: `accounts`, `core`, `forms`, `processes`, `reports`
- write flow: API / presentation → Service → ORM
- read flow: API / presentation → Selector → ORM
- business transaction boundaries belong in Services
- post-commit side effects use `transaction.on_commit(...)`
- Forms must remain independent from Processes

## Infrastructure roles

Redis is used for:

- cache
- Celery broker
- Channels layer

WebSocket use is scoped to real-time reporting.

## API

- REST
- version prefix: `/api/v1/`
- OpenAPI / Swagger documentation

## Engineering workflow

Long-lived branches:

- `main` — stable milestone/release/baseline branch
- `dev` — integration branch for normal ongoing development

Normal development flow:

```text
Issue
→ short-lived branch from dev
→ implementation + tests
→ Pull Request to dev
→ review
→ CI
→ merge to dev
```

Milestone promotion flow:

```text
dev
→ Pull Request to main
→ review
→ CI
→ merge to main
```

Rules:

- no normal direct development on `main`
- no normal direct development on `dev`
- CI runs on Pull Requests and pushes for both long-lived branches
- frozen CI check names: `lint`, `test`, `migration-check`
- native GitHub branch protection is not required while unavailable on the current private-repository plan
- PR/review/CI policy remains authoritative even without native branch-protection enforcement

## Configuration

Environment variables are read by settings/configuration only. Business/service code must not read
host environment variables directly.

## Change control

This baseline must not be silently edited. Structural changes require a Change Record and, when
necessary, a superseding architecture baseline.
