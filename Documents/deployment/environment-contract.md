# Environment Contract

**Historical origin:** Gate 2C — Settings & Environment Foundation  
**Status:** ACTIVE FOUNDATION RECORD  
**Active baseline:** BL-FOUNDATION-003  
**Historical baselines:** BL-FOUNDATION-001 and BL-FOUNDATION-002  
**Applied extensions:** CHG-0003 (Redis/Celery), CHG-0004 (production email), CHG-0006 (production topology, proxy trust and bounded dependency configuration)

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
- `REDIS_CACHE_URL`
- `CELERY_BROKER_URL`

There are intentionally no database credential fallbacks.

## Environment-specific variables

Development and production use:

- `DJANGO_ALLOWED_HOSTS`

Optional in development and required in production where documented:

- `DJANGO_CSRF_TRUSTED_ORIGINS`

Production security:

- `DJANGO_SECURE_SSL_REDIRECT` — defaults to true; explicit false only for disposable HTTP smoke
- `DJANGO_TRUST_NGINX_PROXY` — defaults to false; production Compose explicitly enables it because Nginx is the sole ingress and overwrites the protocol header

Production email delivery (authorized by CHG-0004 and applied by Issue #26):

- `DJANGO_EMAIL_HOST` — required SMTP hostname
- `DJANGO_EMAIL_PORT` — required positive integer
- `DJANGO_EMAIL_HOST_USER` — required SMTP username
- `DJANGO_EMAIL_HOST_PASSWORD` — required SMTP secret
- `DJANGO_EMAIL_USE_TLS` — optional boolean, defaults to `true`
- `DJANGO_EMAIL_TIMEOUT` — required positive finite integer in seconds
- `DJANGO_DEFAULT_FROM_EMAIL` — required sender identity

Production maps these values through Django's built-in SMTP backend. `EMAIL_TIMEOUT` must always be
finite; the production contract does not permit Django's unlimited/`None` SMTP timeout.

The SMTP password remains a host secret. `.env.example` contains placeholders only.

## Redis logical separation

The architecture reserves separate Redis logical databases/URLs:

- `REDIS_CACHE_URL` — cache
- `CELERY_BROKER_URL` — Celery broker
- `CHANNEL_LAYER_URL` — Channels layer

The current settings layer actively consumes:

- `REDIS_CACHE_URL` through Django's built-in Redis cache backend;
- `CELERY_BROKER_URL` through Celery.

`CHANNEL_LAYER_URL` remains reserved in the environment contract and Docker/CI runtime for the
optional Channels Redis wiring authorized by CHG-0003 if bonus Issue #41 is implemented later.
Issue #41 is explicitly deferred optional BONUS scope for Gate 4 as well; HTTP reporting remains authoritative.

Test settings replace the Redis cache backend with deterministic Django `LocMemCache`, so tests do
not depend on Redis availability.

## Docker development behavior

Compose reads repository-root `.env` values for interpolation.

Inside the Docker network, the web service overrides infrastructure locations:

- `POSTGRES_HOST=postgres`
- `POSTGRES_PORT=5432`
- `REDIS_CACHE_URL=redis://redis:6379/0`
- `CELERY_BROKER_URL=redis://redis:6379/1`
- `CHANNEL_LAYER_URL=redis://redis:6379/2`
- `PYTEST_ADDOPTS=-p no:cacheprovider` for Docker-only pytest cache hygiene

The web service does **not** export `DJANGO_SETTINGS_MODULE`.

Therefore:

- `python src/manage.py ...` uses the development default from `manage.py`;
- Daphne-backed `runserver` uses development settings;
- `pytest` is free to use `config.settings.test` from `pyproject.toml`.

This prevents Docker development configuration from accidentally overriding the test runner.

## Email backend behavior

The environment-specific email behavior is:

- development → Django console email backend;
- test → Django local-memory email backend;
- production → Django SMTP email backend configured only through the settings/environment boundary.

Application Services and Celery tasks use Django's email abstraction and do not read SMTP
environment variables directly.

## Test settings

`config.settings.test`:

- still uses PostgreSQL;
- never falls back to SQLite;
- forces a deterministic test-only Django secret after base settings import;
- forces `CELERY_BROKER_URL = "memory://"` even when CI/Docker inject a development broker URL;
- provides a bootstrap `REDIS_CACHE_URL` for base-settings import and then replaces the cache
  backend with deterministic Django `LocMemCache`;
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


## Gate 4 dependency bounds

Both base/development and production settings receive bounds through configuration;
readiness/business code does not read host environment variables directly.
Malformed or out-of-range values fail settings import without echoing the value.

| Environment value | Default | Valid integer range | Applied boundary |
| --- | --- | --- | --- |
| POSTGRES_CONNECT_TIMEOUT_SECONDS | 2 seconds | 2–10 | Django PostgreSQL OPTIONS/connect_timeout |
| READINESS_DB_QUERY_TIMEOUT_MS | 1000 ms | 100–5000 | Disposable readiness connection statement_timeout |
| REDIS_CONNECT_TIMEOUT_SECONDS | 1 second | 1–5 | Configured Django Redis cache socket_connect_timeout |
| REDIS_SOCKET_TIMEOUT_SECONDS | 1 second | 1–5 | Configured Django Redis cache socket_timeout |

The probe connection also uses Linux TCP keepalive/user timeout settings. Business
queries do not inherit its statement timeout. Cache timeout retries are disabled.
PostgreSQL connect bounds apply per resolved host/address, not as a global DNS or
multi-host deadline. The supported topology uses one internal dependency service;
see [health and logging](health-and-logging.md) for verified failure behavior.

## Separate production Compose configuration

Use `.env.production.example` as the placeholder contract and untracked
`.env.production` for operator values. `compose.production.yaml` explicitly sets
`DJANGO_SETTINGS_MODULE=config.settings.production` for init/web/worker/Beat,
internal PostgreSQL host/port, cache DB 0 and broker DB 1. The default image tag is
`local`; optional `PRODUCTION_IMAGE_TAG` identifies the image built from repository
files. No real .env file, credential or source bind mount belongs in the image.

| Compose environment value | Default | Meaning |
| --- | --- | --- |
| NGINX_BIND_ADDRESS | 127.0.0.1 | Only published HTTP ingress address |
| PRODUCTION_HTTP_PORT | 8080 | Nginx host port; change local origin values with it |
| NGINX_PROXY_SCHEME | http | Validated constant protocol forwarded to Django |
| PRODUCTION_IMAGE_TAG | local | Shared init/web/Celery image tag |

In `https` mode the Nginx startup guard requires loopback ingress and a trusted,
operator-managed TLS edge as its only caller. It does not infer HTTPS from a
client-supplied header. Production settings enable secure cookies, explicit hosts
and origins, DEBUG=False and STATIC_ROOT=/app/staticfiles inside the image.

Static settings are derived from repository paths, not arbitrary business-code
environment reads. The named static volume is writable in init and read-only in
web/Nginx. SSL redirect is secure by default. HTTP smoke requires explicit false
and retains secure cookies; it is not a complete HTTPS authentication test.
Start/verify/update/cleanup commands and the TLS trust conditions are documented
in [production deployment](production.md).
