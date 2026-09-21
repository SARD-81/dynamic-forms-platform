# Docker Development Foundation

**Gate:** 2H — Docker Development Foundation  
**Status:** IN PROGRESS  
**Target baseline:** BL-FOUNDATION-001

## Scope

The development Compose topology intentionally contains exactly three services:

- `web`
- `postgres`
- `redis`

The following are intentionally deferred:

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
- starts Django's development `runserver`

Because `daphne` is first in `INSTALLED_APPS`, the installed Daphne integration owns Django's
`runserver` command and serves the ASGI application during development.

The source bind mount plus Django/Daphne development autoreload means Python source edits are
observed without rebuilding the image.

### postgres

- image: `postgres:16-alpine`
- persistent named volume: `postgres_data`
- health checked with `pg_isready`

### redis

- image: `redis:7-alpine`
- health checked with `redis-cli ping`

## Environment behavior

Compose reads project values from the repository-root `.env` file through normal Compose variable
interpolation.

The web container intentionally overrides network locations:

- PostgreSQL host → `postgres`
- Redis cache → `redis:6379/0`
- Celery broker → `redis:6379/1`
- Channels layer reservation → `redis:6379/2`

This preserves the local non-Docker `.env` contract where PostgreSQL/Redis may use
`127.0.0.1`.

## First-time setup

Create the local environment file if it does not exist.

Linux/macOS/Fish:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Set real local values for at least:

- `DJANGO_SECRET_KEY`
- `POSTGRES_PASSWORD`

Then:

```bash
docker compose up --build
```

The web service waits for healthy PostgreSQL and Redis, applies migrations, and starts the
development server at:

```text
http://localhost:8000
```

## Daily commands

Start:

```bash
docker compose up
```

Start in background:

```bash
docker compose up -d
```

Follow web logs:

```bash
docker compose logs -f web
```

Run tests:

```bash
docker compose exec web pytest
```

Run Django checks:

```bash
docker compose exec web python src/manage.py check
```

Open a Django shell:

```bash
docker compose exec web python src/manage.py shell
```

Stop containers:

```bash
docker compose down
```

## Destructive local reset

The following command deletes the Docker-managed PostgreSQL development volume:

```bash
docker compose down -v
```

Use it only when intentionally resetting local Docker data.

## Verification

Before GATE 2H can close:

```bash
docker compose --env-file .env config --quiet
docker compose build
docker compose up -d
docker compose ps
docker compose exec web python src/manage.py check
docker compose exec web pytest
docker compose logs web
```

Confirm that:

- PostgreSQL is healthy;
- Redis is healthy;
- web remains running;
- migrations apply;
- HTTP responds on port 8000;
- editing a Python source file triggers development autoreload.

## Cross-platform rule

Docker documentation must use direct `docker compose` commands.

Make/WSL wrappers may be added later only as optional conveniences.
