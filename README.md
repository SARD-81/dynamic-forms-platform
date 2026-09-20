# Dynamic Forms Platform

A private team project for building and managing dynamic forms, multi-step workflows, submissions, reporting, scheduled delivery, and real-time report updates with Django.

## Project status

- GATE 0 — **CLOSED** — BL-ARCH-001 FROZEN
- GATE 1 — **CLOSED** — BL-DATA-002 FROZEN / AUTHORITATIVE
- GATE 2 — **OPEN**
  - 2A — **CLOSED**
  - 2B — **IN PROGRESS**
  - target — BL-FOUNDATION-001

## Team

- SARD-81 — Team Lead / Owner
- Mahsa-Alipour — Developer
- amirrezaparvaneh — Developer

External observers are outside project ownership and workload.

## Runtime baseline

- Python 3.12
- Django 5.2 LTS
- Django REST Framework
- Django Channels + Daphne
- Psycopg 3 / PostgreSQL

## Application layout

```text
src/
├── manage.py
├── config/
│   ├── settings/
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

The Custom User is defined before the first project migration.

## Local bootstrap

Python 3.12 is required.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements/base.txt
```

Linux/macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements/base.txt
```

Fish:

```fish
python3.12 -m venv .venv
source .venv/bin/activate.fish
python -m pip install --upgrade pip
python -m pip install -r requirements/base.txt
```

No SQLite configuration is used. PostgreSQL must be available before database commands such as `migrate`.

Basic check:

```bash
python src/manage.py check
```

Development server:

```bash
python src/manage.py runserver
```

Daphne is first in `INSTALLED_APPS`, so the development server uses its ASGI integration.

## Workflow

Issue → short-lived branch → implementation/tests → PR → CI → peer review → merge.

The GATE 2A merge was an explicit owner exception. Subsequent work returns to peer approval before merge once collaborator invitations are accepted.

## Cross-platform policy

Make may later be provided only as an optional convenience. Official commands cannot depend on Make or WSL.

## Documentation

The authoritative ERD source is `Documents/database/erd.nomnoml`.

Frozen baselines are never edited silently; approved structural changes require Change Records and superseding baselines when needed.
