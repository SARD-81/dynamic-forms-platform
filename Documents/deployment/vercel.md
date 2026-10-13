# Vercel deployment

This additive profile is authorized by [CHG-0008](../project-control/change-records/CHG-0008.md).
The existing [Docker production guide](production.md) remains supported.

## Infrastructure

- Vercel project: `dynamic-forms-platform`, team `sard-81s-projects`, region `fra1`.
- Neon project: `dynamic-forms-production`, PostgreSQL 16, Frankfurt.
- Runtime uses the pooled Neon hostname, TLS and no persistent Django connections.
  The bounded disposable readiness probe uses POSTGRES_DIRECT_HOST, because
  PgBouncer rejects statement_timeout in connection startup options.
- `config.cache.AtomicDatabaseCache` stores shared cache data in `dynamic_forms_cache`.
- Vercel builds the ASGI entrypoint and private Celery subscriber in `pyproject.toml`.
- Daily Cron calls `/internal/cron/reports/` at 03:00 UTC (06:30 Tehran).
- SMTP uses Gmail with a Google App Password over STARTTLS on port 587.

## Configuration

See `.env.vercel.example` for required names. Populate real values in Vercel's
encrypted environment configuration. Use an independent database for preview
testing that changes data; do not run automated test suites on production.
`DJANGO_SECRET_KEY`, `CRON_SECRET`, database password and SMTP password must
never be committed. Preview host/origin entries come from Vercel's own URL variables,
including `VERCEL_PROJECT_PRODUCTION_URL`. Explicitly include each stable project
alias in `DJANGO_ALLOWED_HOSTS` and its HTTPS origin in `DJANGO_CSRF_TRUSTED_ORIGINS`.
A team slug is a hostname suffix separated by a hyphen, not a subdomain; a value
such as `.sard-81s-projects.vercel.app` does not match project aliases.

## Gmail and App Password

1. Enable [2-Step Verification](https://myaccount.google.com/security) on the sender
   account, then create a dedicated [App Password](https://myaccount.google.com/apppasswords)
   named `Dynamic Forms Vercel`. Use the generated password without spaces.
2. Open this project's Vercel **Settings → Environment Variables** and replace
   the previous SMTP configuration for Production (and Preview if needed):

   | Variable | Value |
   | --- | --- |
   | `DJANGO_EMAIL_HOST` | `smtp.gmail.com` |
   | `DJANGO_EMAIL_PORT` | `587` |
   | `DJANGO_EMAIL_USE_TLS` | `true` |
   | `DJANGO_EMAIL_HOST_USER` | Full Gmail sender address |
   | `DJANGO_EMAIL_HOST_PASSWORD` | App Password, marked Sensitive |
   | `DJANGO_DEFAULT_FROM_EMAIL` | `Dynamic Forms <same Gmail address>` |
   | `DJANGO_EMAIL_TIMEOUT` | `10` |

3. Save the variables together, then redeploy the reviewed Production commit.
   Changing environment variables does not update an existing deployment.
4. Register with a recipient address you control, verify receipt of the OTP and
   complete activation. Test a periodic report to an authorized recipient and
   confirm delivery plus successful `last_sent_at` advancement.

Ordinary Gmail sending does not require ownership of a custom sending domain or
Resend DNS verification. Use the same authenticated Gmail address as the sender.
Do not paste the App Password into chat, Git, logs or documentation. Google revokes
App Passwords after the account password changes. Availability can be restricted
by organizational policies, security-key-only 2FA or Advanced Protection.
See [Google's App Password documentation](https://support.google.com/accounts/answer/185833)
and [Gmail SMTP configuration](https://support.google.com/a/answer/176600).
The existing production preflight instantiates the SMTP backend but does not
authenticate or prove delivery; Gmail credential entry and real delivery must be
recorded separately from deployment readiness.

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
  --base-url https://dynamic-forms-platform-tan.vercel.app \
  --liveness-path /health/live/ --readiness-path /health/ready/ \
  --static-path /static/core/app.css --timeout 20 --require-all
```

Additionally verify login with enforced CSRF, owner CRUD/builder/publication,
private unlock, anonymous process resume, LINEAR/FREE execution and reports.
Unauthorized Cron must return 401. An authenticated Cron request must enqueue
the task and the private subscriber must complete it; observe actual execution,
not only the 202 response. Weekly/monthly delivery remains at least once.

Check production URL health and both application/static 404s for `.env` and
source files. Confirm actual Gmail receipt for OTP and scheduled reports, not only
an SMTP connection or an enqueued task. Never log OTP, passwords, form answers or resume tokens.

## Limits

Hobby Cron runs daily and invocation timing may drift. HTTP/subscriber functions
have finite duration; retries fit within the configured 300-second limit.
PostgreSQL cache adds database queries and suits this small bootcamp deployment;
for larger traffic provision Redis and switch DJANGO_CACHE_BACKEND to redis.
Neon cold starts need the configured connection timeout. Runtime logs and Neon
restore history support diagnosis and recovery; periodic independent backups
remain an operator responsibility.
