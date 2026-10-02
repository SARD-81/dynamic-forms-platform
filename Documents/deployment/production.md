# Production deployment

The production entrypoint is `compose.production.yaml`. It is separate from the
five-service development `compose.yaml`; neither command set changes the other.
CHG-0006 authorizes this seven-role topology and the operational health contract.

| Role | Responsibility | Published host port |
| --- | --- | --- |
| `app-init` | migrate, collectstatic, production_preflight; exits 0 only when all pass | none |
| `web` | existing ASGI application on Daphne, production settings | none |
| `nginx` | application proxy and collected `/static/` files | configurable HTTP ingress |
| `celery-worker` | report task execution | none |
| `celery-beat` | hourly due-report dispatch | none |
| `postgres` | authoritative data, persistent volume | none |
| `redis` | cache DB 0, broker DB 1, persistent broker storage | none |

The application image installs existing base dependencies and copies only `src/`.
It runs as UID 10001, uses no source bind mount, and defaults to Daphne. Nginx's
configuration is built into its own image. `static_data` is writable only in
`app-init` and read-only in Nginx/web. Its sole content is Django-collected assets;
source, templates, environment files and database files are never copied there.

`app-init` uses `sh -ec` and `collectstatic --noinput --clear`: the collected static
destination is cleared before collection, so retained volumes cannot keep obsolete
or future-dated assets during an update or rollback. Migration, collection or
preflight failure stops the
remaining sequence and prevents web/worker/Beat startup through Compose's
`service_completed_successfully` dependency. PostgreSQL and Redis must first pass
their finite healthchecks. Do not run multiple Beat instances against one database.

## Configuration and HTTPS trust

Copy `.env.production.example` into an untracked `.env.production`, then supply
real deployment values through that file or the host environment. Shell environment
values override Compose's env file. Secrets are never built into images. Use
explicit allowed hosts and trusted CSRF origins for the actual deployment.

Production keeps `DEBUG=False`, secure session/CSRF cookies and HTTPS redirects
enabled by default. `DJANGO_TRUST_NGINX_PROXY` is false outside this topology;
Compose explicitly enables it because Daphne has no published port and Nginx
overwrites the forwarded-protocol header. Never enable it for an independently
public Django/Daphne listener. Arbitrary client `X-Forwarded-Proto`,
`X-Forwarded-Host`, `Forwarded` and forwarded IP values are not trusted.

This stack does not issue certificates or configure an external TLS provider.
Its default HTTP ingress binds to `127.0.0.1:8080`. For real HTTPS, place an
operator-managed TLS edge on the same host, restrict this ingress to that edge,
and set `NGINX_PROXY_SCHEME=https`. This constant means **every request arriving
at Nginx has already passed the trusted TLS edge**. Keep SSL redirect true. The
edge must accept/redirect plain HTTP before forwarding and must not allow direct
untrusted callers to this ingress. Do not combine `https` mode with an unrestricted
public HTTP binding. In plain HTTP/local smoke use `http`; explicitly disabling
SSL redirect is required and applies only to that disposable smoke environment.

Nginx overwrites `X-Forwarded-Proto` with the configured validated `http`/`https`
mode; it never copies the incoming header. Proxy connect/read/send timeouts are
3/15/15 seconds. Docker DNS is re-resolved on a finite cache interval, so a web
container replacement does not leave Nginx pointing permanently at an old IP.
Upgrade headers are compatible with future #41 work, but no
WebSocket report implementation is claimed. HTTP reporting remains authoritative.

Nginx access logs omit query strings/referers. Per-request Nginx error logs and
Daphne access logs are disabled because they can include resume tokens in URLs.
Safe access statuses, application exception logs and container state retain
operational diagnostics. See [health and logging](health-and-logging.md).

## Local production smoke

Prerequisites: Docker Engine/Desktop with Compose v2 supporting
`service_completed_successfully`, Python 3.12 on the host, and an unused local
port 8080. Commands run from the repository root. On Windows PowerShell use
`Copy-Item` in place of `cp`.

```bash
cp .env.production.example .env.production
```

For a local smoke, use disposable placeholder credentials and set
`DJANGO_SECURE_SSL_REDIRECT=false`, `NGINX_PROXY_SCHEME=http`,
`DJANGO_CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8080` in that untracked file. Secure
cookies remain enabled, so complete browser authentication needs real HTTPS;
the HTTP smoke verifies unauthenticated/public reachability and production internals.

```bash
docker compose --project-name dynamic-forms-production --env-file .env.production -f compose.production.yaml config --quiet
docker compose --project-name dynamic-forms-production --env-file .env.production -f compose.production.yaml up --build -d
docker compose --project-name dynamic-forms-production --env-file .env.production -f compose.production.yaml ps -a
python scripts/verify_production_runtime.py --env-file .env.production --project-name dynamic-forms-production
python scripts/verify_production.py --base-url http://127.0.0.1:8080 --liveness-path /health/live/ --readiness-path /health/ready/ --static-path /static/core/app.css --timeout 5 --require-all
```

If initialization fails, inspect its container status and sanitized application
logs before retrying. Do not bypass `app-init` or replace it with `runserver`.
The runtime verifier checks applied migrations, collected project/admin assets,
production settings, internal ports, worker response/task registration and Beat
state. It calls #79 preflight. Public checks stay in the reusable #82 verifier.
Neither verifier sends email or dispatches a report task. A fresh smoke database
has no subscriptions, and CI uses `smtp.invalid` rather than a delivery service.

## Stop, update and cleanup

For ordinary stops preserve data:

```bash
docker compose --project-name dynamic-forms-production --env-file .env.production -f compose.production.yaml down --remove-orphans
```

Back up PostgreSQL before deploying an update that runs migrations. Rebuild and
start the topology to rerun initialization. A code rollback does not automatically
undo database migrations; this Gate adds no domain migrations. Use an earlier
verified image/configuration with its compatible database and retain the data volumes.

Only for disposable local/CI smoke, remove the volumes as well:

```bash
docker compose --project-name dynamic-forms-production --env-file .env.production -f compose.production.yaml down -v --remove-orphans
```

`-v` deletes the database, broker and static volumes. Never use it as a production
update/rollback command. CI always tears down its own isolated smoke project.

## Frozen acceptance and release status

BL-FOUNDATION-003 and BL-RELEASE-001 freeze the implemented topology at
`f62cce74c67053ec2e2af06fb3ed75bd20a3ca00`. Mandatory production-smoke runs alongside
the existing development job and verifies initialization, internal services,
public routes/static, outages and proxy security. See the
[acceptance record](../testing/gate4-acceptance-verification.md) for exact run IDs
and limits of the evidence. Gate 4 is CLOSED/FROZEN; milestone
[PR #103](https://github.com/SARD-81/dynamic-forms-platform/pull/103) records the
separately authorized main promotion and its final verification. TLS certificates, actual deployment secrets,
backups and real SMTP/API destinations remain operator configuration.
