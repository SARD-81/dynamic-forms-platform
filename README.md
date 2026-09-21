# Dynamic Forms Platform

A private team project for building and managing dynamic forms, multi-step workflows, submissions,
reporting, scheduled delivery, and real-time report updates with Django.

## Project status

- GATE 0 — **CLOSED** — BL-ARCH-002 FROZEN / AUTHORITATIVE
- GATE 1 — **CLOSED** — BL-DATA-002 FROZEN / AUTHORITATIVE
- GATE 2 — **OPEN**
  - 2A–2G — **CLOSED**
  - 2H — **IN PROGRESS**
  - target — BL-FOUNDATION-001

## Runtime baseline

- Python 3.12
- Django 5.2 LTS
- Django REST Framework
- Django Channels + Daphne
- PostgreSQL
- Redis
- Celery
- Ruff
- pytest
- GitHub Actions
- Docker Compose development foundation

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

## Local environment

Python 3.12 is required for non-Docker development.

Install development dependencies:

```bash
python -m pip install -r requirements/dev.txt
```

Create the local environment file.

Linux/macOS/Fish:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Generate a local Django secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Put it in `.env` and replace the PostgreSQL password placeholder.

## Docker development

The development topology contains exactly:

- web
- postgres
- redis

Start it with direct Docker Compose commands:

```bash
docker compose up --build
```

Then open:

```text
http://localhost:8000
```

The web container waits for healthy PostgreSQL and Redis, applies migrations, and runs the
Daphne-backed Django ASGI development server. The repository is bind-mounted for development
autoreload.

Useful commands:

```bash
docker compose ps
docker compose logs -f web
docker compose exec web python src/manage.py check
docker compose exec web pytest
docker compose down
```

See `Documents/deployment/docker-development.md` for the complete development-container workflow.

## Non-Docker verification

With a valid local `.env`:

```bash
ruff check .
ruff format --check .
pytest
python src/manage.py makemigrations --check --dry-run
```

## Settings modules

Development default:

```text
config.settings.development
```

Test:

```text
config.settings.test
```

Production:

```text
config.settings.production
```

## Configuration boundary

Only settings/configuration may read environment variables.

Business code, Services, Selectors, views, and models must not call `os.getenv()` directly.

See `Documents/deployment/environment-contract.md`.

## Workflow

Normal development:

```text
Issue → branch from dev → implementation/tests → PR to dev → CI → review → merge to dev
```

Milestone promotion:

```text
dev → PR to main → CI → review → merge to main
```

See BL-ARCH-002 and `CONTRIBUTING.md`.

## Documentation

The authoritative ERD source is `Documents/database/erd.nomnoml`.

Frozen baselines are never edited silently; approved structural changes require Change Records and
superseding baselines when needed.
