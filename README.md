# Dynamic Forms Platform

A private team project for building and managing dynamic forms, multi-step workflows, submissions,
reporting, scheduled delivery, and a production-ready Django deployment path. Real-time report
updates through Channels/WebSockets remain optional bonus scope and are not required for
application correctness or Gate 4 closure.

## Project status

- GATE 0 — **CLOSED** — BL-ARCH-002 FROZEN / AUTHORITATIVE
- GATE 1 — **CLOSED** — BL-DATA-002 FROZEN / AUTHORITATIVE
- GATE 2 — **CLOSED** — BL-FOUNDATION-001 FROZEN / HISTORICAL FOUNDATION
- GATE 3 — **CLOSED / FROZEN / PROMOTED TO MAIN** — BL-FOUNDATION-002 + BL-APPLICATION-001; technical freeze `72d5af1b5f26d9d3b8ba67605d96a69605878dcc`; milestone main commit `419e71961ad68a7cca9b0ef04a13501ef6c4b8cd`
- GATE 4 — **IN PROGRESS** — Production Readiness, Release Hardening & Bonus Enhancements; tracker #77

Gate 3 delivered and froze the mandatory application feature set and was promoted through PR #76.

Gate 4 closes the remaining production-delivery gap from the original project brief: a real
production mode, production-oriented web serving, production settings/static collection, Docker and
environment-owned configuration. Reverse-proxy usage such as Nginx is bonus scope in the brief;
this project deliberately selects Nginx as the Gate 4 public reverse-proxy/static boundary because
it provides a coherent release topology and supports later optional WebSocket proxying.

See [Gate 4 execution plan](Documents/project-control/gate4-execution-plan.md).

## Current Gate 4 state

- #79 production preflight command/tests — **COMPLETED**, merged through PR #88; CI #200 green;
- #80 health/readiness/logging — implementation exists in Draft PR #87 but runtime changes are
  blocked from merge until #78 / CHG-0006 and branch synchronization;
- #89 / CHG-0007 — Gate 4 Team Lead Verification governance transition;
- #78 / CHG-0006 — next mandatory production-runtime authorization task;
- #81 — production ASGI/Nginx/collectstatic implementation after #78;
- #82 — reusable external production HTTP/static verifier;
- #83 — mandatory production-smoke CI;
- #84 — final production acceptance, baseline freeze and milestone promotion;
- #41 — optional real-time reporting bonus.

## Implemented Gate 3 capabilities

- Django account registration, email OTP activation, login and logout;
- owner-scoped categories;
- unlimited dynamic Forms with TEXT, NUMBER, SELECT and CHECKBOX questions;
- Form publish/close lifecycle, PUBLIC/PRIVATE access and unique participant links;
- anonymous and authenticated Form submissions with validated Answers;
- LINEAR and FREE Processes composed from Forms;
- anonymous token resume and authenticated Process resume;
- Form analytics, response browsing and aggregate question reports;
- Process analytics, ProcessRun browsing and completion metrics;
- DRF API v1 with OpenAPI schema and Swagger UI;
- Redis-backed participant/report caching with explicit invalidation and database fallback;
- staff-managed WEEKLY/MONTHLY report subscriptions;
- Celery/Beat scheduled EMAIL/API report delivery with bounded retry behavior;
- final browser FREE-flow and one-time resume-token hardening;
- clean five-service Docker bootstrap/runtime smoke verification in CI.

HTTP reporting remains authoritative. Issue #41 is optional BONUS/STRETCH scope.

The authoritative Gate 3 acceptance map is
[Gate 3 acceptance verification](Documents/testing/gate3-acceptance-verification.md).

## Gate 4 ownership

- Mahsa-Alipour — #79 production preflight (done) and #82 reusable production HTTP/static verifier;
- amirrezaparvaneh — #80 health/readiness/logging and #83 production CI verification;
- SARD-81 — #89 governance, #78 production change control, #81 ASGI/Nginx/static/security topology,
  optional #41 real-time integration, and #84 final acceptance/baselines/promotion.

All Django Template/HTML/presentation-specific JavaScript work remains owned by SARD-81.

## Runtime baseline entering Gate 4

- Python 3.12
- Django 5.2 LTS
- Django REST Framework
- Django Channels + Daphne
- PostgreSQL 16
- Redis 7
- Celery + Celery Beat
- Ruff
- pytest + pytest-django
- GitHub Actions
- Docker Compose

The active frozen Gate 3 foundation is `BL-FOUNDATION-002`. Gate 4 production-runtime changes must
first be authorized by #78 / CHG-0006 and may only become a new active foundation after verified
implementation and a superseding baseline.

## Quick Start — Docker development

This remains the recommended development path. The production-oriented Gate 4 runtime is not
claimed complete until #78–#83 are implemented and verified.

Prerequisite: Docker Engine/Desktop with Docker Compose v2.

### 1. Clone and select the integration branch

```bash
git clone https://github.com/SARD-81/dynamic-forms-platform.git
cd dynamic-forms-platform
git switch dev
```

### 2. Create the local environment file

Linux/macOS/Fish:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and replace local placeholders such as `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD`.
Never commit real secrets.

### 3. Validate and start development topology

```bash
docker compose --env-file .env config --quiet
docker compose up --build -d
docker compose ps
```

Expected development services:

- `postgres` — healthy
- `redis` — healthy
- `web` — running on port 8000
- `celery-worker` — running
- `celery-beat` — running

Open `http://localhost:8000/` and `http://localhost:8000/admin/login/`.

### 4. Verify development foundation

```bash
docker compose exec web python src/manage.py check
docker compose exec web pytest
docker compose logs --tail=100 celery-worker
docker compose logs --tail=100 celery-beat
```

The stable CI `docker-smoke` job performs a clean build, starts the five-service development topology,
verifies Celery worker/task registration and smoke-tests critical HTML/API/OpenAPI routes.

Gate 4 #83 adds a separate production-topology `production-smoke`; it does not replace this
development check.

Stop the development stack with:

```bash
docker compose down
```

## Application layout

```text
src/
├── manage.py
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── test.py
│   │   └── production.py
│   ├── env.py
│   ├── celery.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── urls.py
└── apps/
    ├── accounts/
    ├── core/
    ├── forms/
    ├── processes/
    └── reports/
```

## Non-Docker development

Python 3.12 and PostgreSQL are required.

```bash
python -m pip install -r requirements/dev.txt
ruff check .
ruff format --check .
pytest
python src/manage.py makemigrations --check --dry-run
```

Celery outside Docker:

```bash
celery --workdir=src -A config worker --loglevel=INFO
celery --workdir=src -A config beat --loglevel=INFO --schedule=/tmp/celerybeat-schedule
```

## Settings modules

- development: `config.settings.development`
- test: `config.settings.test`
- production: `config.settings.production`

Django management commands default to development settings. pytest uses the test settings module.

## Workflow

After CHG-0007 becomes effective, Gate 4 normal work uses:

```text
Issue → branch from current dev → implementation/tests → PR to dev → required CI green → Team Lead Verification → explicit Team Lead merge decision
```

Milestone promotion uses:

```text
dev → PR to main → all required Gate 4 CI green → Team Lead Verification → explicit Team Lead merge decision
```

Independent peer approval is optional and no reviewer is auto-requested merely to satisfy process.
Material automated/manual findings must still be resolved or explicitly accepted with evidence.

CHG-0005 remains the historical Gate 3 governance record; CHG-0007 explicitly governs Gate 4 only
after its transition PR is merged.

See [CONTRIBUTING.md](CONTRIBUTING.md),
[Gate 4 execution plan](Documents/project-control/gate4-execution-plan.md), and
[CHG-0007](Documents/project-control/change-records/CHG-0007.md).

## Foundation and verification documentation

- [Gate 4 execution plan](Documents/project-control/gate4-execution-plan.md)
- [Project gate status](Documents/project-control/gate-status.md)
- [CHG-0007](Documents/project-control/change-records/CHG-0007.md)
- [BL-FOUNDATION-001](Documents/project-control/baselines/BL-FOUNDATION-001.md) — historical Gate 2 foundation
- [BL-FOUNDATION-002](Documents/project-control/baselines/BL-FOUNDATION-002.md) — active frozen Gate 3 foundation entering Gate 4
- [BL-APPLICATION-001](Documents/project-control/baselines/BL-APPLICATION-001.md) — frozen Gate 3 application behavior
- [Gate 3 acceptance verification](Documents/testing/gate3-acceptance-verification.md)
- [Environment contract](Documents/deployment/environment-contract.md)
- [Docker development](Documents/deployment/docker-development.md)
- [CI & branch governance](Documents/deployment/ci-and-branch-governance.md)
- [Quality & test foundation](Documents/testing/quality-test-foundation.md)

Previous frozen baselines are never edited in place. Structural changes require explicit Change
Records and superseding baselines where needed.

## Configuration boundary

Only settings/configuration may read environment variables.

Business code, Services, Selectors, views, APIs, tasks and models must not call `os.getenv()`
directly.
