# Environment Contract

**Gate:** 2C — Settings & Environment Foundation  
**Status:** ACTIVE FOUNDATION RECORD  
**Target baseline:** BL-FOUNDATION-001

## Rule

Only the settings/configuration layer may read host environment variables.

Business logic, Services, Selectors, API views, models, and domain code must not call
`os.getenv()` or otherwise derive host configuration directly.

## Local .env behavior

`src/config/env.py` loads the repository-root `.env` file with `override=False`.

This means:

1. real shell/container environment variables take precedence;
2. `.env` is a local-development convenience;
3. `.env` is ignored by Git;
4. `.env.example` documents the contract and contains no real secret.

## Required base variables

Base settings refuse to start when any of these are missing or empty:

- `DJANGO_SECRET_KEY`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `CELERY_BROKER_URL`

There are intentionally no database credential fallbacks.

## Environment-specific variables

Development and production use:

- `DJANGO_ALLOWED_HOSTS`

Optional in development and required in production where documented:

- `DJANGO_CSRF_TRUSTED_ORIGINS`

Production security:

- `DJANGO_SECURE_SSL_REDIRECT`

## Redis logical separation

The architecture reserves separate Redis logical databases/URLs:

- `REDIS_CACHE_URL` — cache
- `CELERY_BROKER_URL` — Celery broker
- `CHANNEL_LAYER_URL` — Channels layer

The current settings layer actively consumes `CELERY_BROKER_URL`.

`REDIS_CACHE_URL` and `CHANNEL_LAYER_URL` are already present in the environment contract and
Docker/CI runtime, but Django cache and Channels Redis wiring remain future implementation work in
their relevant feature/deployment gates.

## Docker development behavior

Compose reads repository-root `.env` values for interpolation.

Inside the Docker network, the web service overrides infrastructure locations:

- `POSTGRES_HOST=postgres`
- `POSTGRES_PORT=5432`
- `REDIS_CACHE_URL=redis://redis:6379/0`
- `CELERY_BROKER_URL=redis://redis:6379/1`
- `CHANNEL_LAYER_URL=redis://redis:6379/2`

The web service does **not** export `DJANGO_SETTINGS_MODULE`.

Therefore:

- `python src/manage.py ...` uses the development default from `manage.py`;
- Daphne-backed `runserver` uses development settings;
- `pytest` is free to use `config.settings.test` from `pyproject.toml`.

This prevents Docker development configuration from accidentally overriding the test runner.

## Test settings

`config.settings.test`:

- still uses PostgreSQL;
- never falls back to SQLite;
- forces a deterministic test-only Django secret after base settings import;
- forces `CELERY_BROKER_URL = "memory://"` even when CI/Docker inject a development broker URL;
- uses Celery eager execution;
- uses Django's local-memory email backend;
- uses a faster password hasher.

PostgreSQL connection variables still come from the environment so pytest can use the correct local,
Docker, or CI PostgreSQL service.

## Secret generation

A Docker-only cross-platform option is:

```bash
docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Never commit the generated value.
