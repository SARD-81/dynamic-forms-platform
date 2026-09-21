# Foundation Bootstrap Verification

**Gate:** 2I — Developer Workflow, README & Foundation Verification  
**Status:** COMPLETED / PASSED  
**Target baseline:** BL-FOUNDATION-001

## Purpose

Prove that the Gate 2 foundation is usable from a fresh clone without relying on hidden local state.

## Verified environment

- Date: 2026-09-21
- OS: Ubuntu 24.04
- Docker: 29.1.3
- Docker Compose: 2.40.3
- Verification branch before merge: `docs/17-developer-workflow-verification`

## Clean bootstrap result

A fresh clone with no project `.env` or virtual environment successfully completed the documented Docker-first path:

```text
Compose config validation     PASSED
Docker build/start            PASSED
PostgreSQL                    healthy
Redis                         healthy
web                           running
Django system check           PASSED
pytest settings               config.settings.test
pytest                        24/24 PASSED
HEAD /admin/login/            HTTP 200
ASGI server                   Daphne
git status --short            clean
```

The observed bootstrap completed comfortably below the 15-minute target, excluding network/image-download time.

## Findings resolved during Gate 2I

### Docker pytest settings isolation

The Docker web service originally exported `DJANGO_SETTINGS_MODULE=config.settings.development`, which caused container pytest to inherit development settings.

Gate 2I removed that override. Django management commands still default to development through `manage.py`, while pytest now resolves `config.settings.test` from `pyproject.toml`.

A settings-contract test protects this behavior.

### Root-owned pytest cache

The root-running development container initially created `.pytest_cache` on the host bind mount.

The Docker web service now sets:

```text
PYTEST_ADDOPTS=-p no:cacheprovider
```

Focused verification after the fix proved:

```text
docker compose exec web pytest
→ 24 passed
→ settings: config.settings.test

test ! -e .pytest_cache
→ passed

git status --short
→ clean
```

No container-created pytest cache remained on the host.

### Reused PostgreSQL volume after password change

A reused development PostgreSQL volume retained credentials initialized with an older password, while the recreated local `.env` used a new `POSTGRES_PASSWORD`.

PostgreSQL reported healthy, but the web service correctly failed authentication. Resetting the disposable development volume resolved the mismatch:

```bash
docker compose down -v
docker compose up --build -d
```

After recreation, all health, Django, pytest, HTTP, and cache-hygiene checks passed.

This reset procedure is for disposable development data only.

## Independent developer status

Collaborator repository access remained inactive during Gate 2I, so an independent teammate verification could not be assigned through GitHub.

The owner-run fresh-clone verification is accepted for this gate. A teammate may repeat the same README workflow later as an onboarding exercise.

## Gate result

GATE 2I: **COMPLETED / PASSED**.

The documented developer bootstrap is reproducible, uses the correct Django test settings, and no known foundation documentation/runtime mismatch remains.
