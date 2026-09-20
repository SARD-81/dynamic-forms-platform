# Environment Contract

**Gate:** 2C — Settings & Environment Foundation  
**Status:** ACTIVE FOUNDATION RECORD  
**Target baseline:** BL-FOUNDATION-001

## Rule

Only the settings/configuration layer may read host environment variables.

Business logic, Services, Selectors, API views, models, and domain code must not call `os.getenv()` or otherwise derive host configuration directly.

## Local .env behavior

`src/config/env.py` loads the repository-root `.env` file with `override=False`.

This means:

1. real shell/container environment variables take precedence;
2. `.env` is a local-development convenience;
3. `.env` is ignored by Git;
4. `.env.example` documents the required contract and contains no real secret.

## Required base variables

The application refuses to start when any of these are missing or empty:

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

Optional in development, required in production where documented:

- `DJANGO_CSRF_TRUSTED_ORIGINS`

Production security:

- `DJANGO_SECURE_SSL_REDIRECT`

## Redis logical separation

The architecture reserves separate Redis logical databases/URLs:

- `REDIS_CACHE_URL` — cache
- `CELERY_BROKER_URL` — Celery broker
- `CHANNEL_LAYER_URL` — Channels layer

Gate 2C actively consumes only the Celery broker setting. Cache and Channels Redis wiring are implemented in their relevant subgates without changing this contract silently.

## Test settings

`config.settings.test`:

- still uses PostgreSQL;
- never falls back to SQLite;
- uses a test-only Django secret;
- uses Celery's in-memory broker and eager execution;
- uses Django's local-memory email backend;
- may use a faster password hasher.

PostgreSQL connection variables still come from the environment.

## Secret generation

A cross-platform way to generate a local Django secret is:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Never commit the generated value.
