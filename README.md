# Dynamic Forms Platform

Build a form, share its link, and review the responses. When several forms belong
to the same workflow, combine them into a process and let participants complete
the steps in order or choose their own order.

This is a Django application with both a browser interface and a REST API.
PostgreSQL stores the data; Redis supports caching and the Celery report-delivery
runtime. Development and production have separate Docker Compose entrypoints.

## Project status

Gate 3's mandatory application behavior is complete and frozen. Gate 4 is
**CLOSED / FROZEN on `dev`**, with production acceptance recorded at technical
freeze point `df5609b17f8238661b7cc464228f5837ce7f4537` and **502 passing tests**.
The final `dev → main` milestone remains pending the Team Lead's manual merge;
[Tracker #77](https://github.com/SARD-81/dynamic-forms-platform/issues/77) and
[Issue #84](https://github.com/SARD-81/dynamic-forms-platform/issues/84) stay open until that promotion.

See [Gate 4 acceptance](Documents/testing/gate4-acceptance-verification.md),
[BL-FOUNDATION-003](Documents/project-control/baselines/BL-FOUNDATION-003.md) and
[BL-RELEASE-001](Documents/project-control/baselines/BL-RELEASE-001.md) for the
verified runtime and release evidence.

The engineering record is in [Documents](Documents/README.md). Earlier frozen
baselines remain unchanged. Real-time WebSocket reporting (#41) is deferred
optional scope; HTTP reports remain the source of truth.

## What the application does

| Area | Available behavior |
| --- | --- |
| Accounts | Registration, email OTP activation, login, logout and current-user details |
| Categories | Owner-scoped organization of forms and processes |
| Form builder | TEXT, NUMBER, SELECT and CHECKBOX questions, required fields, validation and ordered options |
| Form lifecycle | Draft, publication, closure, public links and password-protected private access |
| Submissions | Anonymous or authenticated participation, validated answers and a receipt |
| Processes | LINEAR or FREE steps composed from forms, progress tracking and resume |
| Reports | Visits, responses, process completion, aggregate answers and detailed response/run browsing |
| Scheduled delivery | Staff-managed weekly/monthly subscriptions delivered by email or an API request |
| API | Session-authenticated DRF API v1, OpenAPI schema and Swagger UI |
| Operations | Liveness/readiness, bounded dependency checks, secret-safe application logs and production verification |

Forms and processes belong to their owners. A participant link is an entrypoint,
not permission to inspect owner reports. Private access secrets and anonymous
resume tokens are handled separately from public identifiers.

Anonymous process resume has a one-time token disclosure contract. Save the token
when it is first returned; a previously saved token is not displayed again after
a browser restart. Authenticated participants resume through their account.
The detailed rules are in the
[participant access contract](Documents/architecture/participant-access-cache-contract.md).

## Run it for development

You need Git and Docker Engine/Desktop with Docker Compose v2. The development
image includes Python 3.12 and the development/test tools; a host Python installation
is optional when you use this path.

### 1. Get the integration branch and create your local environment

```bash
git clone https://github.com/SARD-81/dynamic-forms-platform.git
cd dynamic-forms-platform
git switch dev
cp .env.example .env
```

On Windows PowerShell, replace the final command with:

```powershell
Copy-Item .env.example .env
```

Set `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` to local values in the untracked
`.env`. The example file contains placeholders. Keep the local host/origin values
unless you deliberately change the address where you open the site.

### 2. Build and start

```bash
docker compose --env-file .env config --quiet
docker compose --env-file .env up --build -d
docker compose --env-file .env ps
```

The web service applies migrations before starting the development server.
PostgreSQL, Redis, a Celery worker and one Beat scheduler start with it.

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/).
If port 8000 is occupied, free that port or adjust the development port mapping
and the corresponding local CSRF origin together.

### 3. Create an account or an administrator

Register through `/accounts/register/`. Development uses Django's console email
backend, so the activation email appears in the local web container output:

```bash
docker compose --env-file .env logs --tail=100 web
```

Use the code on the verification page, then log in. Production sends this email
through configured SMTP; it does not use the console email backend.

For Django admin and staff report-subscription management:

```bash
docker compose --env-file .env exec web python src/manage.py createsuperuser
```

This is interactive. No sample administrator or default account is seeded.

### 4. Try the main flows

1. Create a category if you need one, then create a form.
2. Add questions and options in the builder. Publish the form when it is ready.
3. Open the participant link in a separate browser session, submit answers, and
   inspect the owner's response list and report.
4. Create a LINEAR or FREE process from forms, publish it, and try participant
   progress/resume. LINEAR enforces the next step; FREE allows any unfinished step.
5. As a staff user, preview a weekly/monthly report before creating a delivery
   subscription. Use only destinations you control.

Changing a published resource is constrained by the frozen lifecycle and data
contracts. The builder is not a way to rewrite already-collected answers.

## Useful routes

Use the development origin above or your production HTTPS origin.

| Purpose | Path |
| --- | --- |
| Home | `/` |
| Owner dashboard | `/dashboard/` |
| Register / login | `/accounts/register/` / `/accounts/login/` |
| Forms / processes | `/forms/` / `/processes/` |
| Staff report subscriptions | `/reports/` |
| Django admin | `/admin/` |
| API root | `/api/v1/` |
| OpenAPI JSON | `/api/schema/?format=json` |
| Swagger UI | `/api/v1/docs/` |
| Liveness / readiness | `/health/live/` / `/health/ready/` |

The API uses Django sessions and CSRF protection. Protected endpoints can return
403 for an unauthenticated session. See
[API conventions](Documents/api/api-conventions.md) and the generated schema for
the resource-specific routes and request bodies.

## Test and check the project

With the development topology running:

```bash
docker compose --env-file .env exec -T web pytest
docker compose --env-file .env exec -T web ruff check .
docker compose --env-file .env exec -T web ruff format --check .
docker compose --env-file .env exec -T web python src/manage.py check
docker compose --env-file .env exec -T web python src/manage.py makemigrations --check --dry-run
```

Tests use `config.settings.test`, PostgreSQL, a deterministic in-memory cache,
local-memory email and eager Celery tasks. PostgreSQL is required; there is no
SQLite fallback. Do not set `DJANGO_SETTINGS_MODULE` to production while running
the test suite.

For native development, use Python 3.12, install
`python -m pip install -r requirements/dev.txt`, and provide reachable PostgreSQL
16 and Redis 7 services plus the same environment contract. Then run the commands
above directly without the Compose prefix. Database users used by pytest need
permission to create the isolated test database. The container path is simpler
when you do not already have those services locally.

Required CI checks are `lint`, `test`, `migration-check`, `docker-smoke` and
`production-smoke`. All must finish successfully on the final PR HEAD.
The development smoke checks the five-service development runtime; the production
smoke builds and exercises the separate seven-role release runtime.

## Run the production topology

Use `compose.production.yaml` and `.env.production.example`; keep the development
Compose file for development. The production application uses
`config.settings.production` and Daphne. It has no source-code bind mounts and
does not use Django's development server.

| Service | Role |
| --- | --- |
| `app-init` | One-shot migrate, collectstatic and production_preflight |
| `web` | Internal Daphne/ASGI application |
| `nginx` | Only published HTTP entrypoint; proxy and collected static |
| `celery-worker` / `celery-beat` | Report worker and one scheduler |
| `postgres` / `redis` | Internal data/cache/broker services |

Initialization must succeed before web/worker/Beat starts. Collected assets live
in `/app/staticfiles`; Nginx mounts that volume read-only at `/srv/static`.
Only Nginx publishes a host port, by default on `127.0.0.1:8080`.

### Configure HTTPS before a real deployment

Production defaults to `DEBUG=False`, secure session/CSRF cookies and HTTPS
redirects. Set explicit allowed hosts, HTTPS CSRF origins, a strong secret key,
database credentials and SMTP configuration.

This repository does not issue TLS certificates. Use an operator-managed TLS
edge on the same host and restrict the Nginx ingress to that edge. In this mode
set `NGINX_PROXY_SCHEME=https` and retain HTTPS redirects. The Nginx startup guard
requires a loopback binding for this mode. Nginx overwrites the protocol header;
it never trusts a value supplied by an arbitrary HTTP client.

The detailed trust, startup, update, rollback and volume contracts are in the
[production guide](Documents/deployment/production.md).

### Disposable local HTTP smoke

Copy the production example into `.env.production`. For this local smoke only,
use disposable credentials and set:

```dotenv
DJANGO_SECURE_SSL_REDIRECT=false
DJANGO_CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8080
NGINX_BIND_ADDRESS=127.0.0.1
NGINX_PROXY_SCHEME=http
PRODUCTION_HTTP_PORT=8080
```

Secure cookies remain on. Public reachability can be tested over this local HTTP
boundary; a complete browser login session should use HTTPS.

```bash
docker compose --project-name dynamic-forms-production --env-file .env.production -f compose.production.yaml config --quiet
docker compose --project-name dynamic-forms-production --env-file .env.production -f compose.production.yaml up --build -d
python scripts/verify_production_runtime.py --env-file .env.production --project-name dynamic-forms-production
python scripts/verify_production.py --base-url http://127.0.0.1:8080 --liveness-path /health/live/ --readiness-path /health/ready/ --static-path /static/core/app.css --timeout 5 --require-all
```

The runtime verifier checks the containers/settings/migrations/static/Celery
contract and calls the existing preflight. The public verifier checks the HTTP
boundary without printing response bodies or credentials. Neither sends an email
or triggers a report delivery.

## Health, logging and operational behavior

GET and HEAD are supported on both health routes; HEAD returns no body. Other
methods return 405. Liveness is independent of backing services. Readiness checks a disposable
PostgreSQL connection and the configured Django cache. Both success routes return
`{"status":"ok"}`; dependency failure returns generic
`503 {"status":"not_ready"}`.

Default PostgreSQL connect timeout is 2 seconds per resolved host/address; the
probe query timeout is 1000 ms. Redis connect/read timeouts default to 1 second.
Settings validate the configurable ranges. The supported production topology uses
one internal service for each dependency. See
[health and logging](Documents/deployment/health-and-logging.md) for bounds and caveats.

Django, application and Celery logs go to the container console with redaction
for named credentials/tokens, parameterized messages, exceptions and stack text.
Nginx access logs omit query strings; raw per-request Nginx error and Daphne
access logs are disabled to keep participant resume tokens out of those streams.
Avoid logging raw request bodies, cookies, answers or unlabeled private values.

## Stop and keep your data

```bash
docker compose --env-file .env down --remove-orphans
docker compose --project-name dynamic-forms-production --env-file .env.production -f compose.production.yaml down --remove-orphans
```

Run the command for the topology you started. Data volumes are retained.
Adding `-v` removes the database and other runtime volumes; use that only for
disposable development/CI data. Back up PostgreSQL before deployment updates.
A code rollback does not undo migrations.

If startup fails, inspect `ps -a` and the relevant application's sanitized logs.
An `app-init` failure is a startup blocker, not a step to skip. If health works but
a browser cannot complete login, check the HTTPS/cookie/origin configuration.
If periodic delivery stops, verify worker response, task registration and the
single Beat scheduler with the runtime verifier.

## Repository map and engineering record

| Location | Contents |
| --- | --- |
| `src/apps/accounts/` | Users, authentication and OTP |
| `src/apps/core/` | Categories, participant access, health/logging and preflight |
| `src/apps/forms/` | Form authoring, submissions and reports |
| `src/apps/processes/` | Process authoring, execution/resume and reports |
| `src/apps/reports/` | Subscriptions, periodic payloads and delivery tasks |
| `src/config/` | Settings, environment boundary, ASGI and Celery |
| `src/templates/` | Shared browser interface |
| `tests/` | Cross-application/configuration/tooling regression tests |
| `scripts/` | Public HTTP and internal production runtime verifiers |
| `docker/nginx/` | Production proxy image/configuration |
| `Documents/` | ERD, contracts, baselines, decisions and acceptance evidence |

Start with the [document index](Documents/README.md), the
[ERD](Documents/database/erd.svg), the
[environment contract](Documents/deployment/environment-contract.md), and
[CI/governance](Documents/deployment/ci-and-branch-governance.md).

Only settings/configuration reads host environment variables. Services/selectors
own domain behavior; transport and presentation layers use those contracts.
Frozen baselines are historical records and are superseded through explicit
change control rather than rewritten.

The original team is SARD-81, Mahsa-Alipour and amirrezaparvaneh. Gate 4 completion
work preserves their accepted application/tooling contributions. Final operational
finishing tasks [#95](https://github.com/SARD-81/dynamic-forms-platform/issues/95)
and [#96](https://github.com/SARD-81/dynamic-forms-platform/issues/96) were originally assigned
to AmirReza and completed in this closeout, including HEAD health support and
safe verifier cancellation. No contributor task remains open.

