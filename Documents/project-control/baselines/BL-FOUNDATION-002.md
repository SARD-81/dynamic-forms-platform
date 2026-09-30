# BL-FOUNDATION-002 — Gate 3 Engineering Foundation Baseline

**Status:** FROZEN / AUTHORITATIVE  
**Approved:** 2026-09-30  
**Gate:** GATE 3 — Application Feature Implementation  
**Architecture dependency:** BL-ARCH-002  
**Data dependency:** BL-DATA-002  
**Supersedes for active foundation state:** BL-FOUNDATION-001  
**Technical freeze point:** `dev @ 72d5af1b5f26d9d3b8ba67605d96a69605878dcc`

## Decision

BL-FOUNDATION-002 is the authoritative active engineering-foundation baseline after the mandatory Gate 3 runtime/configuration extensions were implemented and verified.

BL-FOUNDATION-001 remains immutable historical evidence for the Gate 2 foundation. This baseline does not rewrite it; it records the actually applied state authorized by CHG-0003 and CHG-0004 and the active merge-governance state established by CHG-0005.

The technical state frozen here already exists at the freeze point above. The documentation-only freeze PR introduces no application/runtime behavior change.

## Direct dependency constraints

The active runtime dependency constraints are:

```text
Django>=5.2.17,<5.3
djangorestframework>=3.18.1,<3.19
channels[daphne]>=4.3.2,<4.4
psycopg[binary]>=3.3.6,<3.4
celery[redis]>=5.6.3,<5.7
python-dotenv>=1.2.3,<1.3
drf-spectacular==0.27.1
```

Development dependencies remain defined by `requirements/dev.txt` and include Ruff, pytest, pytest-django and coverage.

No `channels-redis` dependency is present because optional Issue #41 is deferred from Gate 3 closure.

## Settings and environment contract

The settings architecture remains split into:

- `config.settings.base`;
- `config.settings.development`;
- `config.settings.test`;
- `config.settings.production`.

Environment access remains restricted to settings/configuration. Business/domain code, Services, Selectors, APIs, tasks and models do not own host-environment reads.

The active Redis role separation is:

```text
DB 0 → Django cache
DB 1 → Celery broker
DB 2 → reserved for Channels only if optional real-time reporting is implemented later
```

PostgreSQL remains the source of truth. Cache state is optimization-only and may not become application authority.

CHG-0004's vendor-neutral production email configuration contract is applied in settings. Production deployment itself remains outside Gate 3 scope.

## Active development runtime

The verified Docker Compose development topology contains exactly five active services:

```text
web
postgres
redis
celery-worker
celery-beat
```

### web

- built from the repository-root `Dockerfile`;
- waits for healthy PostgreSQL and Redis;
- applies Django migrations;
- serves the ASGI application through Django/Daphne development `runserver`;
- publishes host port 8000.

### celery-worker

- reuses the application image;
- command: `celery --workdir=src -A config worker --loglevel=INFO`;
- uses Redis logical DB 1 through `CELERY_BROKER_URL`;
- waits for PostgreSQL and Redis health.

### celery-beat

- reuses the application image;
- command: `celery --workdir=src -A config beat --loglevel=INFO --schedule=/tmp/celerybeat-schedule`;
- uses the same Celery broker configuration;
- runs separately from the worker; Beat is not embedded with `-B`.

### postgres / redis

- PostgreSQL 16 Alpine with persistent development volume and health check;
- Redis 7 Alpine with health check;
- neither service is published to the host by the repository Compose configuration.

Nginx, production orchestration and Kubernetes remain out of scope.

## Cache foundation

Gate 3 activates Django cache behavior through the framework cache abstraction and `REDIS_CACHE_URL` in development/runtime configuration.

Frozen rules:

- DB records remain authoritative;
- domain code does not instantiate ad-hoc Redis clients;
- passwords, OTPs and raw anonymous resume tokens are not cache payloads;
- cache keys/invalidation are feature-owned and regression tested;
- test settings remain deterministic and do not require Redis-backed cache correctness for ordinary unit/integration execution.

## Celery / scheduled execution foundation

Celery + Celery Beat are the mandatory scheduled-execution mechanism for Gate 3 report delivery.

Frozen runtime behavior includes:

- Beat dispatches the due-subscription check hourly;
- worker tasks perform EMAIL/API delivery;
- bounded retry/backoff and per-subscription failure isolation;
- `last_sent_at` changes only after successful external delivery;
- API delivery is documented as at-least-once and carries a deterministic period-level `Idempotency-Key`.

No Celery result backend or `django-celery-beat` dependency is introduced.

## Channels state

Django Channels + Daphne remain installed as part of the architecture foundation, but Redis-backed channel layers and WebSocket report consumers are not part of this mandatory freeze.

Issue #41 is optional BONUS/STRETCH and is explicitly deferred. HTTP reporting is authoritative and complete without WebSockets.

## CI / quality foundation

The active stable CI jobs are:

- `lint`;
- `test`;
- `migration-check`;
- `docker-smoke`.

### lint

```bash
ruff format --check .
ruff check .
```

### test

Runs the full pytest suite against PostgreSQL/Redis service infrastructure using `config.settings.test`.

### migration-check

```bash
python src/manage.py check
python src/manage.py makemigrations --check --dry-run
docker compose --env-file .env.example config --quiet
```

### docker-smoke

From a clean runner it:

- builds the repository image;
- starts all five development services;
- waits for Django readiness;
- verifies all five services are running;
- verifies Celery worker ping and scheduled-report task registration;
- smoke-tests login, API root and OpenAPI;
- asserts mandatory Gate 3 REST/OpenAPI paths, including Form and Process reporting;
- always tears down containers and volumes.

## Verification evidence at freeze

Closure-candidate PR #74 was Team Lead reviewed and squash-merged to produce the technical freeze point `72d5af1b5f26d9d3b8ba67605d96a69605878dcc`.

Final candidate CI run #183 demonstrated:

```text
lint                    PASS
full pytest             365/365 PASS
Django system check     PASS
migration drift check   PASS
Compose validation      PASS
docker-smoke            PASS
5-service topology      PASS
Celery worker ping      PASS
scheduled task registry PASS
critical HTTP routes    PASS
runtime OpenAPI paths   PASS
```

The documentation-only freeze PR must also remain green before Team Lead merge authorization.

## Branch governance

CHG-0005 is the active Gate 3 governance rule:

```text
Issue
→ short-lived branch from current dev
→ implementation/tests
→ PR
→ required CI green
→ Team Lead Verification
→ explicit Team Lead merge decision
```

Independent peer approval is optional and is not a merge/DoD/Gate-closure prerequisite. Material automated/manual findings must still be resolved or explicitly accepted before merge.

The same Team Lead Verification model applies to the Gate 3 `dev → main` milestone PR.

## Data and migration state

BL-DATA-002 remains the authoritative data baseline. Gate 3 did not silently replace its domain model.

The repository continues to require:

```bash
python src/manage.py makemigrations --check --dry-run
```

as a closure/CI guard against model-migration drift.

## Change-control mapping

- CHG-0003 — mandatory Redis cache + Celery worker/Beat runtime applied; optional Channels portion deferred with #41;
- CHG-0004 — production email settings/environment contract applied;
- CHG-0005 — Team Lead Verification governance applied.

Future structural changes to this active foundation require a new Change Record and, when appropriate, a superseding foundation baseline. BL-FOUNDATION-001 and BL-FOUNDATION-002 must not be silently rewritten.

**GATE 3 FOUNDATION FREEZE — COMPLETE**
