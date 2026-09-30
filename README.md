# Dynamic Forms Platform

A private team project for building and managing dynamic forms, multi-step workflows, submissions,
reporting, scheduled delivery, and production-ready Django deployment. Real-time report updates
through Channels/WebSockets remain optional bonus scope and are not required for application
correctness or Gate 4 closure.

## Project status

- GATE 0 — **CLOSED** — BL-ARCH-002 FROZEN / AUTHORITATIVE
- GATE 1 — **CLOSED** — BL-DATA-002 FROZEN / AUTHORITATIVE
- GATE 2 — **CLOSED** — BL-FOUNDATION-001 FROZEN / HISTORICAL FOUNDATION
- GATE 3 — **CLOSED / FROZEN / PROMOTED TO MAIN** — BL-FOUNDATION-002 + BL-APPLICATION-001; technical freeze `72d5af1b5f26d9d3b8ba67605d96a69605878dcc`; milestone main commit `419e71961ad68a7cca9b0ef04a13501ef6c4b8cd`
- GATE 4 — **IN PROGRESS** — Production Readiness, Release Hardening & Bonus Enhancements; tracker #77

Gate 3 delivered and froze the mandatory application feature set and was promoted from `dev` to
`main` through milestone PR #76 after green CI and Team Lead Verification.

Gate 4 closes the production-delivery gap intentionally left outside Gate 3: production ASGI
serving without Django `runserver`, `collectstatic`, Nginx reverse proxy/static serving,
operational health/readiness, reusable production verification tooling and automated production
smoke verification.

See [Gate 4 execution plan](Documents/project-control/gate4-execution-plan.md).

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

Issue #41 real-time reporting through Channels/WebSockets is carried into Gate 4 as explicitly
optional BONUS/STRETCH scope. HTTP reporting remains authoritative.

The authoritative Gate 3 acceptance map is
[Gate 3 acceptance verification](Documents/testing/gate3-acceptance-verification.md).

## Gate 4 ownership

- Mahsa-Alipour — production preflight command/tests (#79) and reusable production HTTP/static
  verifier (#82);
- amirrezaparvaneh — health/readiness/logging (#80) and production CI verification (#83);
- SARD-81 — production change control (#78), ASGI/Nginx/static/security topology (#81), optional
  real-time integration (#41), and final acceptance/baselines/promotion (#84).

All Django Template/HTML/presentation-specific JavaScript work remains owned by SARD-81.

Wave 1 starts with #78, #79 and #80 in parallel. #79 is deliberately isolated from production
Nginx/Compose implementation so Mahsa can contribute development code without blocking #81.

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

This is the recommended first-time development path. The production-oriented Gate 4 runtime is not
claimed as complete until the corresponding Gate 4 Issues are implemented and verified.

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

Edit `.env` and replace these two placeholders with local-only values:

- `DJANGO_SECRET_KEY`
- `POSTGRES_PASSWORD`

If you want Docker itself to generate random values:

```bash
docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(50)); print(secrets.token_urlsafe(24))"
```

Use the first line as `DJANGO_SECRET_KEY` and the second as `POSTGRES_PASSWORD`.

### 3. Validate and start

```bash
docker compose --env-file .env config --quiet
docker compose up --build -d
docker compose ps
```

Expected development state:

- `postgres` — healthy
- `redis` — healthy
- `web` — running on port 8000
- `celery-worker` — running and consuming from Redis logical DB 1
- `celery-beat` — running the default Beat scheduler

Open:

```text
http://localhost:8000/
```

The Django admin remains available at:

```text
http://localhost:8000/admin/login/
```

### 4. Verify the development foundation and scheduled-report runtime

```bash
docker compose exec web python src/manage.py check
docker compose exec web pytest
docker compose logs --tail=100 celery-worker
docker compose logs --tail=100 celery-beat
```

pytest must report:

```text
settings: config.settings.test
```

and the suite must pass. Docker disables pytest's cache provider so the root-running container does
not leave root-owned `.pytest_cache` files in the host checkout.

The Beat scheduler dispatches the periodic-report due check once per hour. The due rule itself
prevents duplicate WEEKLY/MONTHLY delivery inside a completed period. Development email delivery
uses Django's console backend, so scheduled EMAIL reports appear in `celery-worker` logs without
requiring SMTP credentials.

To run only the application dependencies and Celery processes explicitly:

```bash
docker compose up -d postgres redis
docker compose up -d web celery-worker celery-beat
```

Stop the stack:

```bash
docker compose down
```

A first clean bootstrap should complete in under 15 minutes, excluding image-download/network time.
The CI `docker-smoke` job also performs a clean image build, starts the complete five-service
development topology, verifies the Celery worker/task registry, and smoke-tests critical HTML/API
and mandatory OpenAPI routes on every PR to `dev` or `main`.

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
├── templates/
│   ├── base.html
│   ├── dashboard/
│   ├── includes/
│   └── public/
└── apps/
    ├── accounts/
    ├── core/
    │   └── static/core/
    ├── forms/
    ├── processes/
    └── reports/
```

The shared Django Template shell, partials, static-asset conventions, and integration rules are
documented in
[Shared presentation template contract](Documents/architecture/presentation-template-contract.md).

Gate 3 account registration uses an inactive User plus email OTP activation, followed by normal
Django password/session login. The complete flow and route contract are documented in
[Authentication and email OTP contract](Documents/architecture/authentication-otp-contract.md).

The periodic reporting payload, due rule, EMAIL/API delivery behavior, retry bounds, and
at-least-once/idempotency contract are documented in
[Periodic report contract](Documents/architecture/periodic-report-contract.md).

## Non-Docker development

Python 3.12 and a PostgreSQL development role/database are required.

Install dependencies:

```bash
python -m pip install -r requirements/dev.txt
```

With a valid local `.env`:

```bash
ruff check .
ruff format --check .
pytest
python src/manage.py makemigrations --check --dry-run
```

To run Celery outside Docker from the repository root:

```bash
celery --workdir=src -A config worker --loglevel=INFO
celery --workdir=src -A config beat --loglevel=INFO --schedule=/tmp/celerybeat-schedule
```

## Settings modules

- development: `config.settings.development`
- test: `config.settings.test`
- production: `config.settings.production`

Django management commands default to development settings. pytest uses the test module configured
in `pyproject.toml`.

## Workflow

Gate 4 development currently follows:

```text
Issue → branch from dev → implementation/tests → PR to dev → required CI green → independent peer review → Team Lead verification → squash merge to dev
```

Gate 4 does not silently extend the Gate 3-only CHG-0005 governance record. A later Gate 4-specific
Change Record may supersede this rule explicitly.

Milestone promotion uses the same active Gate 4 review/verification requirements before explicit
Team Lead merge decision.

See [CONTRIBUTING.md](CONTRIBUTING.md),
[BL-ARCH-002](Documents/project-control/baselines/BL-ARCH-002.md), and
[Gate 4 execution plan](Documents/project-control/gate4-execution-plan.md).

## Foundation and verification documentation

- [Gate 4 execution plan](Documents/project-control/gate4-execution-plan.md) — active production-readiness execution plan
- [BL-FOUNDATION-001](Documents/project-control/baselines/BL-FOUNDATION-001.md) — frozen historical Gate 2 repository & engineering foundation
- [BL-FOUNDATION-002](Documents/project-control/baselines/BL-FOUNDATION-002.md) — active frozen Gate 3 engineering/runtime foundation
- [BL-APPLICATION-001](Documents/project-control/baselines/BL-APPLICATION-001.md) — frozen mandatory Gate 3 application feature baseline
- [Project gate status](Documents/project-control/gate-status.md) — current gate/baseline status
- [Gate 3 acceptance verification](Documents/testing/gate3-acceptance-verification.md) — frozen integrated acceptance evidence
- [Environment contract](Documents/deployment/environment-contract.md)
- [Docker development](Documents/deployment/docker-development.md)
- [Quality & test foundation](Documents/testing/quality-test-foundation.md)
- [CI & branch governance](Documents/deployment/ci-and-branch-governance.md)
- [Foundation bootstrap verification](Documents/deployment/foundation-bootstrap-verification.md)
- [Shared presentation template contract](Documents/architecture/presentation-template-contract.md)
- [Authentication and email OTP contract](Documents/architecture/authentication-otp-contract.md)
- [Periodic report contract](Documents/architecture/periodic-report-contract.md)
- [PostgreSQL constraint verification](Documents/database/postgresql-constraint-verification.md)
- [Rendered ERD](Documents/database/erd.svg)
- [Authoritative ERD source](Documents/database/erd.nomnoml)

Previous frozen baselines are never edited in place. Structural changes require explicit Change
Records and superseding baselines where needed.

## Configuration boundary

Only settings/configuration may read environment variables.

Business code, Services, Selectors, views, APIs, tasks and models must not call `os.getenv()`
directly.

Frozen baselines are never edited silently; approved structural changes require Change Records and
superseding baselines when needed.
