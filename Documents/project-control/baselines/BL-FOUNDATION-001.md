# BL-FOUNDATION-001 — Repository & Engineering Foundation Baseline

**Status:** FROZEN / AUTHORITATIVE  
**Approved:** 2026-09-21  
**Gate:** GATE 2 — Repository & Engineering Foundation  
**Gate status:** CLOSED  
**Architecture dependency:** BL-ARCH-002  
**Data dependency:** BL-DATA-002  
**Technical freeze point:** `dev @ 8689b5610ce9245a8f70c13e76671b28c3bc4b6f`

## Decision

BL-FOUNDATION-001 is the authoritative foundation baseline for the repository after completion of
GATE 2A through GATE 2J.

The technical implementation frozen by this baseline already existed at the technical freeze point
above. GATE 2J is documentation-only and introduces no application/runtime behavior change.

## Repository structure

The frozen foundation uses a repository-root Docker/development layout and a `src/` Django layout.

```text
.
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── pull_request_template.md
│   └── workflows/
│       └── ci.yml
├── Documents/
│   ├── api/
│   ├── architecture/
│   │   └── adr/
│   ├── database/
│   ├── deployment/
│   ├── project-control/
│   │   ├── baselines/
│   │   └── change-records/
│   └── testing/
├── requirements/
│   ├── base.txt
│   └── dev.txt
├── src/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── core/
│   │   ├── forms/
│   │   ├── processes/
│   │   └── reports/
│   ├── config/
│   │   └── settings/
│   │       ├── base.py
│   │       ├── development.py
│   │       ├── test.py
│   │       └── production.py
│   └── manage.py
├── tests/
├── .dockerignore
├── .env.example
├── .gitignore
├── .python-version
├── CONTRIBUTING.md
├── Dockerfile
├── README.md
├── compose.yaml
├── conftest.py
└── pyproject.toml
```

The Docker development artifacts intentionally live at repository root; there is no required
`docker/` subdirectory.

## Direct dependency constraints

The repository freezes direct dependency **constraints**, not a complete transitive lockfile.

### Runtime — `requirements/base.txt`

```text
Django>=5.2.17,<5.3
djangorestframework>=3.18.1,<3.19
channels[daphne]>=4.3.2,<4.4
psycopg[binary]>=3.3.6,<3.4
celery[redis]>=5.6.3,<5.7
python-dotenv>=1.2.3,<1.3
```

### Development — `requirements/dev.txt`

```text
-r base.txt

ruff>=0.16.8,<0.17
pytest>=9.1.1,<9.2
pytest-django>=4.14.0,<4.15
coverage>=7.16.1,<7.17
```

There is no frozen requirements lockfile in GATE 2. Exact transitive package resolution may vary
within these direct constraints.

### Verified runtime evidence

The final foundation verification observed:

- Python 3.12.14
- Django 5.2.17
- pytest 9.1.1
- pytest-django 4.14.0
- PostgreSQL 16 family
- Redis 7 Alpine
- Docker 29.1.3
- Docker Compose 2.40.3

These are verification evidence. The authoritative Python/package compatibility contract remains the
repository files above.

## Settings architecture

Settings modules:

- `config.settings.base` — shared strict base
- `config.settings.development` — local/development mode
- `config.settings.test` — deterministic PostgreSQL test mode
- `config.settings.production` — production security mode

Runtime modes are development, test, and production; `base.py` is their shared foundation.

### Base configuration contract

Base settings require non-empty:

- `DJANGO_SECRET_KEY`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `CELERY_BROKER_URL`

The database backend is PostgreSQL. SQLite is not a project fallback.

The custom user model is:

```text
AUTH_USER_MODEL = accounts.User
```

Timezone persistence uses UTC with `USE_TZ=True`.

### Environment access boundary

`src/config/env.py` may read host environment variables and loads the repository-root `.env` with
`override=False`.

Environment-variable access belongs to settings/configuration only.

Business/domain code, Services, Selectors, models, and API code must not call `os.getenv()` or
derive host configuration directly.

### Development settings

- `DEBUG=True`
- allowed hosts come from the environment
- CSRF trusted origins come from the environment
- console email backend
- `manage.py` defaults to development settings
- ASGI bootstrap defaults to development settings

### Test settings

- PostgreSQL only
- deterministic test-only Django secret
- `CELERY_BROKER_URL = "memory://"`
- Celery eager execution
- local-memory email backend
- fast MD5 password hasher
- `DEBUG=False`
- pytest resolves `config.settings.test` from `pyproject.toml`

### Production settings

- `DEBUG=False`
- allowed hosts required
- CSRF trusted origins required
- secure session cookie
- secure CSRF cookie
- SSL redirect controlled by `DJANGO_SECURE_SSL_REDIRECT`, defaulting to enabled

### Redis configuration state

The environment contract reserves:

- logical DB 0 / `REDIS_CACHE_URL` for cache
- logical DB 1 / `CELERY_BROKER_URL` for Celery broker
- logical DB 2 / `CHANNEL_LAYER_URL` for Channels

At the Gate 2 freeze, Celery broker configuration is active. Django cache wiring and Channels Redis
backend wiring remain later implementation work and are not falsely claimed as completed here.

## ASGI foundation

Daphne/Channels are installed and `daphne` is first in `INSTALLED_APPS`.

`config.asgi.application` uses `ProtocolTypeRouter` with HTTP wired to Django ASGI.

WebSocket routes are not implemented in Gate 2. BL-ARCH-002 reserves WebSockets for real-time
reporting later.

## Quality and test foundation

### Ruff

Frozen configuration:

- target: Python 3.12
- line length: 100
- enabled rule families: E, F, I, UP, B
- generated Django migrations excluded from Ruff formatting/lint ownership

Standard checks:

```bash
ruff format --check .
ruff check .
```

### pytest / pytest-django

Frozen configuration:

- `DJANGO_SETTINGS_MODULE=config.settings.test`
- `pythonpath = ["src"]`
- test paths: `src/apps`, `tests`
- test filenames: `test_*.py`, `*_tests.py`

Gate 2 freezes a green suite of 24 tests:

- 23 PostgreSQL/database-constraint tests
- 1 settings-contract regression test

The settings-contract test protects test isolation for DEBUG, Celery broker, and email backend.

### Coverage

Coverage is configured with branch measurement over `src/apps` and `src/config`, excluding
migrations/tests as documented.

No numeric coverage threshold is frozen in Gate 2. An observed early value of 83% is evidence only,
not a required target.

## CI workflow

GitHub Actions CI runs for:

- Pull Requests targeting `dev`
- Pull Requests targeting `main`
- pushes to `dev`
- pushes to `main`

The three frozen stable job/check names are:

- `lint`
- `test`
- `migration-check`

### lint

```bash
ruff format --check .
ruff check .
```

### test

Uses Python 3.12 with PostgreSQL 16 and Redis 7 service containers, then runs:

```bash
pytest
```

### migration-check

Runs:

```bash
python src/manage.py check
python src/manage.py makemigrations --check --dry-run
docker compose --env-file .env.example config --quiet
```

The GATE 2 foundation completed with these checks green.

## Branch governance

BL-ARCH-002 remains authoritative.

Long-lived branches:

- `main` — stable milestone/release/baseline branch
- `dev` — normal integration branch

Normal development:

```text
Issue
→ short-lived branch from dev
→ implementation + tests
→ Pull Request to dev
→ review
→ CI
→ merge to dev
```

Milestone promotion:

```text
dev
→ Pull Request to main
→ review
→ CI
→ merge to main
```

Native GitHub branch protection is not a Gate 2 requirement because it is unavailable for the current
private repository under the active plan. CHG-0002 records that exception. The documented
PR/review/CI workflow still applies.

## Docker development topology

The frozen Gate 2 development topology contains exactly three Compose services:

```text
web
postgres
redis
```

### web

- image built from repository-root `Dockerfile`
- base image: `python:3.12-slim-bookworm`
- installs `requirements/dev.txt`
- bind mount: repository root → `/app`
- published host port: `8000:8000`
- waits for healthy PostgreSQL and Redis
- applies migrations on startup
- starts Daphne-backed Django development `runserver`
- development autoreload verified
- does not export `DJANGO_SETTINGS_MODULE`
- sets `PYTEST_ADDOPTS=-p no:cacheprovider` to avoid root-owned pytest cache artifacts on the host
- `init: true`

### postgres

- image: `postgres:16-alpine`
- internal port 5432 only; not published to the host
- named volume: `postgres_data`
- healthcheck: `pg_isready`

### redis

- image: `redis:7-alpine`
- internal port 6379 only; not published to the host
- healthcheck: `redis-cli ping`

### Intentionally not part of Gate 2 Compose

- Nginx
- Celery worker service
- Celery Beat service
- production container topology

Those remain later implementation/deployment work.

## Migration baseline

The initial Django migration graph is frozen with one initial project migration in each domain app:

```text
src/apps/accounts/migrations/0001_initial.py
src/apps/core/migrations/0001_initial.py
src/apps/forms/migrations/0001_initial.py
src/apps/processes/migrations/0001_initial.py
src/apps/reports/migrations/0001_initial.py
```

The graph represents the 14 persisted entities frozen by BL-DATA-002.

Gate 2 verification established:

- Django system checks pass
- initial migrations apply successfully to PostgreSQL
- all five project initial migrations are applied
- `makemigrations --check --dry-run` reports no model/migration drift
- PostgreSQL constraint suite passes
- test databases are PostgreSQL, never SQLite

No feature migration beyond this initial foundation is part of BL-FOUNDATION-001.

## Developer bootstrap

### Recommended Docker-first path

From a clone:

```bash
git switch dev
cp .env.example .env
# set local DJANGO_SECRET_KEY and POSTGRES_PASSWORD
docker compose --env-file .env config --quiet
docker compose up --build -d
docker compose ps
docker compose exec web python src/manage.py check
docker compose exec web pytest
```

Expected foundation result:

- PostgreSQL healthy
- Redis healthy
- web running on port 8000
- Django system check clean
- pytest uses `config.settings.test`
- 24 tests pass
- `/admin/login/` responds through Daphne
- Docker pytest does not create host `.pytest_cache`

This path was verified from a fresh clone in Gate 2I.

### Native development path

Python 3.12, PostgreSQL, Redis, and a valid local `.env` are prerequisites.

Linux/Fish example:

```fish
python3.12 -m venv .venv
source .venv/bin/activate.fish
python -m pip install -r requirements/dev.txt
cp .env.example .env
# configure local PostgreSQL/Redis values
python src/manage.py migrate
python src/manage.py check
pytest
python src/manage.py runserver
```

Windows PowerShell activation:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements/dev.txt
Copy-Item .env.example .env
```

README remains the operational bootstrap guide; this baseline freezes its foundation contract.

## Development troubleshooting frozen as known behavior

For disposable development data, if a previously initialized PostgreSQL Docker volume is reused
after changing `POSTGRES_PASSWORD`, PostgreSQL may remain healthy while the web application fails
authentication.

The documented destructive development reset is:

```bash
docker compose down -v
docker compose up --build -d
```

This deletes local development database data and is not a production credential-rotation procedure.

A Compose Bake/buildx warning is non-blocking when the ordinary Docker build succeeds; buildx is not
a Gate 2 requirement.

## Documentation baseline

Gate 2 foundation documentation includes:

- `README.md`
- `CONTRIBUTING.md`
- `Documents/README.md`
- `Documents/deployment/environment-contract.md`
- `Documents/deployment/docker-development.md`
- `Documents/deployment/ci-and-branch-governance.md`
- `Documents/deployment/foundation-bootstrap-verification.md`
- `Documents/testing/quality-test-foundation.md`
- `Documents/database/postgresql-constraint-verification.md`
- `Documents/database/django-model-mapping.md`
- `Documents/database/erd.nomnoml`
- `Documents/database/erd.svg`

The Nomnoml file is the authoritative editable ERD source. The SVG is a review/display artifact.

## Gate 2 merge audit trail

The actual Gate 2 implementation/governance merges are:

| Subgate | PR | Merge commit | Result |
|---|---:|---|---|
| 2A — Repository & Governance | #2 | `852e6294` | CLOSED |
| 2B — Python / Django / ASGI | #4 | `1e77d21` | CLOSED |
| 2C — Settings & Environment | #6 | `533a535` | CLOSED |
| 2D — Models & Initial Migrations | #8 | `9aca5c2` | CLOSED |
| 2E — PostgreSQL Constraint Verification | #10 | `51aa0c4` | CLOSED |
| 2F — Quality & Test Foundation | #12 | `7e6fff6` | CLOSED |
| 2G — CI & Repository Governance | #14 | `ef5b498` | CLOSED |
| 2H — Docker Development Foundation | #16 | `c738a7d4` | CLOSED |
| 2I — Developer Workflow & Verification | #18 | `8689b561` | CLOSED |

These were repository-owner merges while collaborator access remained pending/inactive. They are
documented exceptions, not a replacement for the peer-review policy.

GATE 2J is the documentation-only freeze/closure step that activates this baseline when its Pull
Request merges into `dev`.

## Verification evidence at freeze

The final Gate 2 foundation has demonstrated:

```text
fresh-clone Docker bootstrap       PASS
PostgreSQL                         healthy
Redis                              healthy
web / Daphne                       running
Django system check                PASS
pytest settings                    config.settings.test
pytest                             24/24 PASS
HTTP /admin/login/                 200
Docker pytest host-cache hygiene   PASS
working tree after verification    clean
Ruff format check                  PASS
Ruff lint                          PASS
migration drift check              PASS
Compose config validation          PASS
GitHub Actions CI                  PASS
```

## Explicitly deferred beyond Gate 2

BL-FOUNDATION-001 does **not** claim implementation of:

- feature APIs and `/api/v1/` endpoint set
- Service/Selector business workflows beyond model foundation
- OTP flows
- form/process application services
- submission/process transaction orchestration
- report query/API implementation
- Django Redis cache backend wiring
- Channels Redis backend/websocket routes
- Celery worker/Beat Compose services
- scheduled jobs
- Nginx runtime
- production Docker topology
- OpenAPI generator/runtime documentation
- application UI/templates beyond Django/admin foundation
- Google OAuth
- audit-log stretch work

Some of these are frozen architectural requirements in BL-ARCH-002, but they are intentionally
future implementation work and must not be read as already delivered by Gate 2.

## Change control

BL-FOUNDATION-001 must not be silently rewritten.

Routine feature work may extend the repository while remaining compatible with this baseline.

An intentional change to a frozen foundation contract — including direct dependency bounds,
settings/environment boundaries, long-lived branch governance, frozen CI check names, test-mode
contract, Docker development topology, migration foundation assumptions, or bootstrap contract —
must be explicitly documented.

Structural or semantic changes require a `CHG-XXXX` record and, when appropriate, a superseding
foundation baseline.

**GATE 2 — CLOSED**
