# Dynamic Forms Platform

A private team project for building and managing dynamic forms, multi-step workflows, submissions, reporting, scheduled delivery, and real-time report updates with Django.

## Project status

- GATE 0 — **CLOSED** — BL-ARCH-001 FROZEN
- GATE 1 — **CLOSED** — BL-DATA-002 FROZEN / AUTHORITATIVE
- GATE 2 — **OPEN**
  - 2A — **CLOSED**
  - 2B — **CLOSED**
  - 2C — **IN PROGRESS**
  - target — BL-FOUNDATION-001

## Runtime baseline

- Python 3.12
- Django 5.2 LTS
- Django REST Framework
- Django Channels + Daphne
- Psycopg 3 / PostgreSQL
- Celery 5.6
- python-dotenv

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

## Local setup

Python 3.12 is required.

Create/activate the virtual environment as documented previously, then:

```bash
python -m pip install -r requirements/base.txt
```

Create the local environment file:

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

Put that value in `.env` and replace the PostgreSQL password placeholder with the real local PostgreSQL credential.

No database credential has a settings fallback.

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

## Verification

With a valid local `.env`:

```bash
python src/manage.py check
```

Do not run project migrations until Gate 2D implements the frozen BL-DATA-002 model set.

## Configuration boundary

Only settings/configuration may read environment variables.

Business code, Services, Selectors, views, and models must not call `os.getenv()` directly.

See `Documents/deployment/environment-contract.md`.

## Workflow

Issue → short-lived branch → implementation/tests → PR → CI → peer review → merge.

The 2A and 2B owner merges are recorded exceptions while collaborator invitations remained pending; they do not replace the peer-review rule.

## Documentation

The authoritative ERD source is `Documents/database/erd.nomnoml`.

Frozen baselines are never edited silently; approved structural changes require Change Records and superseding baselines when needed.
