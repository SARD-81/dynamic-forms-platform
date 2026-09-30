# Dynamic Forms Platform

A private team project for building and managing dynamic forms, multi-step workflows, submissions,
reporting, scheduled delivery, and real-time report updates with Django.

## Project status

- GATE 0 — **CLOSED** — BL-ARCH-002 FROZEN / AUTHORITATIVE
- GATE 1 — **CLOSED** — BL-DATA-002 FROZEN / AUTHORITATIVE
- GATE 2 — **CLOSED** — BL-FOUNDATION-001 FROZEN / AUTHORITATIVE
- GATE 3 — **IN PROGRESS** — application feature implementation; no GATE 3 baseline is frozen yet

Active GATE 3 development starts from `dev` and follows the Issue → branch → implementation/tests →
PR → required CI green → Team Lead Verification → squash merge workflow defined by CHG-0005.

## Runtime baseline

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

## Quick Start — Docker development

This is the recommended first-time path.

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

Expected state:

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

### 4. Verify the foundation and scheduled-report runtime

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

Normal development:

```text
Issue → branch from dev → implementation/tests → PR to dev → required CI green → Team Lead Verification → squash merge to dev
```

Milestone promotion:

```text
dev → PR to main → required CI green → Team Lead Verification → squash merge to main
```

Independent peer approval is optional under CHG-0005 and is not auto-requested merely to satisfy
governance.

See [CONTRIBUTING.md](CONTRIBUTING.md),
[BL-ARCH-002](Documents/project-control/baselines/BL-ARCH-002.md), and
[CHG-0005](Documents/project-control/change-records/CHG-0005.md).

## Foundation documentation

- [BL-FOUNDATION-001](Documents/project-control/baselines/BL-FOUNDATION-001.md) — frozen repository & engineering foundation
- [Project gate status](Documents/project-control/gate-status.md) — current gate execution status
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

## Configuration boundary

Only settings/configuration may read environment variables.

Business code, Services, Selectors, views, and models must not call `os.getenv()` directly.

Frozen baselines are never edited silently; approved structural changes require Change Records and
superseding baselines when needed.
