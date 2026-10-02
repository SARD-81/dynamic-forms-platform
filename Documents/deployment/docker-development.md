# Docker Development Runtime

**Historical foundation:** Gate 2H / BL-FOUNDATION-001  
**Current Gate 3 extension:** CHG-0003 / Issue #40  
**Status:** ACTIVE DEVELOPMENT RUNTIME

## Topology evolution

BL-FOUNDATION-001 originally froze the Gate 2 development topology as exactly three services:

- `web`
- `postgres`
- `redis`

CHG-0003 later authorized the mandatory Gate 3 scheduled-delivery extension. Issue #40 applied that authorization without editing the frozen historical baseline.

The active development topology now contains five services:

- `web`
- `postgres`
- `redis`
- `celery-worker`
- `celery-beat`

Nginx and production orchestration remain out of scope.

## Images and runtime

### web

- base image: `python:3.12-slim-bookworm`;
- installs `requirements/dev.txt`;
- exposes port 8000;
- bind-mounts the repository at `/app`;
- waits for PostgreSQL and Redis health;
- runs migrations;
- starts Django's Daphne-backed development `runserver`.

Because `daphne` is first in `INSTALLED_APPS`, its integration owns Django's development `runserver` command and serves the ASGI application.

### celery-worker

- reuses the same application image as `web`;
- waits for PostgreSQL and Redis health;
- uses Redis logical DB 1 through `CELERY_BROKER_URL`;
- command:

```text
celery --workdir=src -A config worker --loglevel=INFO
```

### celery-beat

- reuses the same application image;
- runs a separate default Celery Beat scheduler process;
- uses the same broker configuration;
- command:

```text
celery --workdir=src -A config beat --loglevel=INFO --schedule=/tmp/celerybeat-schedule
```

Beat is intentionally not embedded in the worker with `-B`, and `django-celery-beat` is not required.

### postgres

- image: `postgres:16-alpine`;
- persistent named volume: `postgres_data`;
- health checked with `pg_isready`.

### redis

- image: `redis:7-alpine`;
- health checked with `redis-cli ping`.

PostgreSQL and Redis are not published to host ports.

## Environment behavior

Compose reads project values from repository-root `.env` through normal Compose interpolation.

Inside the Docker network:

- PostgreSQL host → `postgres`;
- Django cache → `redis:6379/0`;
- Celery broker → `redis:6379/1`;
- Channels layer reservation → `redis:6379/2` only if optional Issue #41 is implemented later.

Business/domain code must use Django/Celery/Channels abstractions and must not create ad-hoc Redis clients.

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

- `DJANGO_SECRET_KEY`;
- `POSTGRES_PASSWORD`.

Then:

```bash
docker compose --env-file .env config --quiet
docker compose --env-file .env up --build -d
docker compose --env-file .env ps
```

Expected running services:

```text
web
postgres
redis
celery-worker
celery-beat
```

Open:

```text
http://localhost:8000/
http://localhost:8000/api/v1/
http://localhost:8000/api/v1/docs/
```

## Daily commands

```bash
docker compose --env-file .env up -d
docker compose --env-file .env logs -f web
docker compose --env-file .env logs -f celery-worker
docker compose --env-file .env logs -f celery-beat
docker compose --env-file .env exec web python src/manage.py check
docker compose --env-file .env exec web pytest
docker compose --env-file .env down
```

pytest must report `settings: config.settings.test`.

Inside the Docker web service, pytest's cache provider is disabled through `PYTEST_ADDOPTS=-p no:cacheprovider` so the root-running development container does not create root-owned `.pytest_cache` files in the host bind mount.

## Scheduled-report runtime

Celery Beat runs the periodic-report due dispatcher once per hour. Due selection is period-based, so hourly polling does not generate hourly reports.

Development EMAIL delivery uses Django's console backend. API delivery uses the documented finite timeout, bounded retry policy and deterministic period-level `Idempotency-Key` from the periodic-report contract.

## CI clean-bootstrap verification

Gate 3 Issue #42 adds a permanent `docker-smoke` CI job. From a clean GitHub-hosted runner it:

1. prepares a disposable `.env`;
2. builds the repository image;
3. starts all five development services;
4. waits for containerized Django readiness;
5. verifies all five services are running;
6. executes Celery worker `inspect ping`;
7. verifies scheduled-report task registration;
8. smoke-tests login, API root and OpenAPI schema from the running containerized application;
9. destroys containers and volumes even on failure.

This complements, rather than replaces, the normal pytest/migration/lint checks.

## Destructive local reset

```bash
docker compose --env-file .env down -v
```

This deletes the Docker-managed PostgreSQL development volume.

## Historical Gate 2H evidence

The original three-service Gate 2 foundation was verified on Ubuntu 24.04 with successful image build, PostgreSQL/Redis health, migrations, Django checks, database-constraint tests, HTTP/Daphne response, autoreload, and a clean working tree.

That historical evidence belongs to BL-FOUNDATION-001 and is not rewritten by the Gate 3 runtime extension.

## Cross-platform rule

Documentation uses direct `docker compose` commands. Make/WSL wrappers may exist only as optional conveniences.

## Troubleshooting

### Web exits with PostgreSQL password authentication failure

If `postgres` is healthy but `web` exits with a PostgreSQL password authentication error, check whether `POSTGRES_PASSWORD` changed while an older Docker PostgreSQL volume still exists.

For disposable development data only:

```bash
docker compose --env-file .env down -v
docker compose --env-file .env up --build -d
```

### Worker does not receive tasks

Confirm Redis is healthy and that both `web`/worker use logical DB 1 through the same `CELERY_BROKER_URL`. Then inspect the worker:

```bash
docker compose --env-file .env exec celery-worker \
  celery --workdir=src -A config inspect ping --timeout=10
```

### Bake/buildx warning

A warning that Docker Compose is configured to build using Bake while buildx is unavailable is non-blocking when the ordinary Docker builder completes successfully. The project does not require buildx.
