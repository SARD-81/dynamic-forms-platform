# Docker Development Foundation

**Gate:** 2H — Docker Development Foundation  
**Status:** COMPLETED / PASSED  
**Target baseline:** BL-FOUNDATION-001

## Scope

The development Compose topology intentionally contains exactly three services:

- `web`
- `postgres`
- `redis`

Intentionally deferred:

- Nginx
- Celery worker
- Celery Beat
- production container topology

## Images and runtime

### web

- base image: `python:3.12-slim-bookworm`
- installs `requirements/dev.txt`
- exposes port 8000
- bind-mounts the repository at `/app`
- runs migrations after PostgreSQL is healthy
- starts Django's Daphne-backed development `runserver`

Because `daphne` is first in `INSTALLED_APPS`, the installed Daphne integration owns Django's
`runserver` command and serves the ASGI application during development.

The source bind mount plus Django/Daphne development autoreload means Python source edits are
observed without rebuilding the image.

The web service does not export `DJANGO_SETTINGS_MODULE`. Management commands default to
development settings, while pytest uses `config.settings.test` from `pyproject.toml`.

### postgres

- image: `postgres:16-alpine`
- persistent named volume: `postgres_data`
- health checked with `pg_isready`

### redis

- image: `redis:7-alpine`
- health checked with `redis-cli ping`

PostgreSQL and Redis are not published to host ports, avoiding conflicts with host-installed
services.

## Environment behavior

Compose reads project values from repository-root `.env` through normal Compose interpolation.

Inside the Docker network:

- PostgreSQL host → `postgres`
- Redis cache → `redis:6379/0`
- Celery broker → `redis:6379/1`
- Channels layer reservation → `redis:6379/2`

This preserves the non-Docker local contract where PostgreSQL/Redis may use `127.0.0.1`.

## First-time setup

Linux/macOS/Fish:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Set local values for:

- `DJANGO_SECRET_KEY`
- `POSTGRES_PASSWORD`

Then:

```bash
docker compose --env-file .env config --quiet
docker compose up --build -d
docker compose ps
```

Open:

```text
http://localhost:8000/admin/login/
```

## Daily commands

```bash
docker compose up -d
docker compose logs -f web
docker compose exec web python src/manage.py check
docker compose exec web pytest
docker compose down
```

pytest must report `settings: config.settings.test`.

Inside the Docker web service, pytest's cache provider is disabled through
`PYTEST_ADDOPTS=-p no:cacheprovider`. This prevents the root-running development container from
creating root-owned `.pytest_cache` files in the host bind mount. Host pytest is unaffected.

## Destructive local reset

```bash
docker compose down -v
```

This deletes the Docker-managed PostgreSQL development volume.

## GATE 2H runtime evidence

Verified on Ubuntu 24.04:

- Docker 29.1.3
- Docker Compose 2.40.3
- image build successful
- PostgreSQL healthy
- Redis healthy
- all initial migrations applied
- Django system check passed
- 23 database-constraint tests passed
- `HEAD /admin/login/` returned HTTP 200
- response server was Daphne
- source-file touch triggered StatReloader and Daphne restart
- working tree remained clean

## Cross-platform rule

Documentation uses direct `docker compose` commands.

Make/WSL wrappers may exist only as optional conveniences.
