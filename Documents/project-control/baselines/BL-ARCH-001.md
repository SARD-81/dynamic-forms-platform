# BL-ARCH-001 — Initial Application Architecture Baseline

**Status:** FROZEN  
**Approved:** 2026-09-20  
**Gate:** GATE 0 — Scope & Architecture  
**Gate status:** CLOSED

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

- `main` is the single long-lived branch
- short-lived Issue-linked branches
- Pull Request review
- automated CI
- no normal direct development on main

## Configuration

Environment variables are read by settings/configuration only. Business/service code must not read host environment variables directly.

## Change control

This baseline must not be silently edited. Structural changes require a Change Record and, when necessary, a superseding architecture baseline.
