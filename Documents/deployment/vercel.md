# Vercel deployment

This additive profile is authorized by [CHG-0008](../project-control/change-records/CHG-0008.md).
The existing [Docker production guide](production.md) remains supported.

## Infrastructure

- Vercel project: `dynamic-forms-platform`, team `sard-81s-projects`, region `fra1`.
- Neon project: `dynamic-forms-production`, PostgreSQL 16, Frankfurt.
- Runtime uses the pooled Neon hostname, TLS and no persistent Django connections.
- `config.cache.AtomicDatabaseCache` stores shared cache data in `dynamic_forms_cache`.
- Vercel builds the ASGI entrypoint and private Celery subscriber in `pyproject.toml`.
- Daily Cron calls `/internal/cron/reports/` at 03:00 UTC (06:30 Tehran).
- SMTP uses a dedicated Resend sending credential and verified sender domain.

## Configuration

See `.env.vercel.example` for required names. Populate real values in Vercel's
encrypted environment configuration. Use an independent database for preview
testing that changes data; do not run automated test suites on production.
`DJANGO_SECRET_KEY`, `CRON_SECRET`, database password and SMTP password must
never be committed. Preview host/origin entries come from Vercel's own URL variables.

The sender domain must pass Resend verification before registration email can
work. Use [Resend Domains](https://resend.com/domains) to obtain exact DNS records.
An alternative SMTP provider can be configured through the existing Django variables.

## Initial release

After project linking and environment provisioning, use a reviewed direct Neon
connection for initialization. Keep these operations out of preview build scripts:

```bash
python src/manage.py migrate --settings=config.settings.vercel
python src/manage.py createcachetable --settings=config.settings.vercel
python src/manage.py check --deploy --settings=config.settings.vercel
python src/manage.py makemigrations --check --dry-run --settings=config.settings.vercel
```

Create the owner's administrator with `createsuperuser` in a private terminal.
Do not bake an administrator password or auto-activation bypass into the app.
Vercel collects static files automatically during the Django build. Deploy the
reviewed Git commit, inspect build status/logs, and verify all public boundaries
before making the production deployment public.

## Verification

```bash
python scripts/verify_production.py \
  --base-url https://dynamic-forms-platform.vercel.app \
  --liveness-path /health/live/ --readiness-path /health/ready/ \
  --static-path /static/core/app.css --timeout 20 --require-all
```

Additionally verify login with enforced CSRF, owner CRUD/builder/publication,
private unlock, anonymous process resume, LINEAR/FREE execution and reports.
Unauthorized Cron must return 401. An authenticated Cron request must enqueue
the task and the private subscriber must complete it; observe actual execution,
not only the 202 response. Weekly/monthly delivery remains at least once.

Check production URL health and both application/static 404s for `.env` and
source files. Use Resend logs to verify real email acceptance and delivery after
DNS verification. Never log OTP, passwords, form answers or resume tokens.

## Limits

Hobby Cron runs daily and invocation timing may drift. HTTP/subscriber functions
have finite duration; retries fit within the configured 300-second limit.
PostgreSQL cache adds database queries and suits this small bootcamp deployment;
for larger traffic provision Redis and switch DJANGO_CACHE_BACKEND to redis.
Neon cold starts need the configured connection timeout. Runtime logs and Neon
restore history support diagnosis and recovery; periodic independent backups
remain an operator responsibility.
