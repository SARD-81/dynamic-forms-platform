# Dynamic Forms Platform

A private team project for building and managing dynamic forms, multi-step workflows, submissions, reporting, scheduled delivery, and real-time report updates with Django.

## Project status

- GATE 0 — Scope & Architecture: **CLOSED**
  - BL-ARCH-001 — **FROZEN**
- GATE 1 — Domain & Data Architecture: **CLOSED**
  - BL-DATA-001 — superseded
  - CHG-0001 — **APPROVED / APPLIED**
  - BL-DATA-002 — **FROZEN / AUTHORITATIVE**
- GATE 2 — Repository & Engineering Foundation: **OPEN**
  - current subgate: **2A — Repository & Governance Bootstrap**
  - target: **BL-FOUNDATION-001**

## Team

- SARD-81 — Team Lead / Owner
- Mahsa-Alipour — Developer
- amirrezaparvaneh — Developer

External observers are not part of project ownership, workload, or required review rules.

## Frozen architecture

The project uses a modular monolith:

- Django
- Django REST Framework
- Django Channels
- Celery / Celery Beat
- PostgreSQL
- Redis
- Django Templates + Vanilla JavaScript
- Nginx
- Docker Compose
- OpenAPI / Swagger
- GitHub Actions

Code flow is intentionally simple and explicit:

- API / presentation → Service → ORM
- API / presentation → Selector → ORM
- transaction boundaries in Service functions
- side effects scheduled with `transaction.on_commit(...)`

## Development workflow

```text
Issue
  ↓
Short-lived branch
  ↓
Implementation + tests
  ↓
Pull Request
  ↓
CI
  ↓
Peer review
  ↓
Merge to main
```

No normal development is performed directly on `main`.

## Gate 2 plan

- 2A — Repository & Governance Bootstrap
- 2B — Python / Django / ASGI Bootstrap
- 2C — Settings & Environment Foundation
- 2D — Frozen Data Models & Migration Foundation
- 2E — Database Constraint Verification
- 2F — Quality & Test Foundation
- 2G — CI & Repository Protection
- 2H — Docker Development Foundation
- 2I — Developer Workflow, README & Foundation Verification
- 2J — BL-FOUNDATION-001 Freeze

## Cross-platform policy

The repository may include a Makefile for convenience, but development never depends on `make`. The official README commands must remain directly usable on Windows and Linux through tools such as `docker compose`, Python, and Git.

## Documentation

Frozen architecture and data decisions live under `Documents/`.

The authoritative ERD source is:

`Documents/database/erd.nomnoml`

Do not change a frozen baseline silently. Structural changes require a `CHG-XXXX` record and, when approved, a superseding baseline.
