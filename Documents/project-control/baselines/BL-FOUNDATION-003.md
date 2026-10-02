# BL-FOUNDATION-003 — Production-ready engineering foundation

**Status:** FROZEN / AUTHORITATIVE ON DEV  
**Verified:** 2026-10-02 UTC  
**Gate:** Gate 4 — Production Readiness  
**Technical freeze point:** `dev@df5609b17f8238661b7cc464228f5837ce7f4537`  
**Supersedes for active foundation:** BL-FOUNDATION-002  
**Dependencies:** BL-ARCH-002, BL-DATA-002, BL-APPLICATION-001  
**Applied authorization:** CHG-0006 and CHG-0007

## Decision and activation

Freeze the engineering/runtime foundation actually implemented and verified after
#80/#81/#83 and final #95/#96 integration. The SHA above is the final technical merge, not the
subsequent documentation activation commit. This baseline activates when the
verified #84 closure/freeze PR is Squash merged into dev under the owner's explicit
Team Lead authorization. Main promotion remains pending and separately authorized.

BL-FOUNDATION-001 and BL-FOUNDATION-002 remain immutable historical evidence.
BL-APPLICATION-001 remains authoritative for form/process/report/auth/participant
semantics. No domain schema/migration or application baseline change is introduced.

## Frozen foundation

- Existing Python 3.12 and Django/DRF/Channels-Daphne/PostgreSQL/Redis/Celery stack;
  dependency constraints remain in requirements/base.txt, unchanged by Gate 4.
  No channels-redis or additional runtime package is added.
- Five-role development compose.yaml and Gate 3 docker-smoke remain intact.
- Separate compose.production.yaml: app-init, web, nginx, celery-worker,
  celery-beat, postgres, redis. Production images are built from repository
  files; application image copies only src and runs as UID 10001. No source binds.
- Init runs migrate --noinput, collectstatic --noinput and production_preflight;
  successful completion gates web/worker/Beat. Persistent PostgreSQL/Redis and
  collected static use named volumes; static is read-only outside init.
- Production ASGI uses Daphne and config.settings.production, never runserver.
- Only Nginx publishes an HTTP port, loopback 8080 by default; Postgres/Redis/
  Daphne/Celery are internal. Finite Nginx proxy timeouts and Docker DNS refresh.
- Nginx serves only collected /static assets; dot/private/source exposure denied.
- DEBUG=False, explicit allowed hosts/origins, secure cookies and SSL redirect
  on by default. Proxy trust opt-in outside Compose, narrowly enabled within
  the sole-ingress topology. Protocol headers are overwritten; HTTPS mode
  requires loopback-only ingress behind an operator-managed trusted TLS edge.
- Settings/configuration owns all environment reads; placeholder-only production
  example. Existing SMTP environment contract preserved, no actual secrets.
- PostgreSQL connect timeout default 2s (range 2–10), readiness query 1000ms
  (100–5000) and Linux TCP bounds on disposable probe connections. Configured
  Django Redis cache socket connect/read default 1s (1–5), no timeout retry.
- GET/HEAD liveness independent of dependencies; readiness DB/cache success 200,
  safe generic failure 503, UUID probe keys and cleanup. HEAD is bodyless;
  unsupported methods are 405 without probing.
- Console logging redacts credentials/tokens including parameterized exceptions/
  stack text; Celery retains configured logging. Raw unsafe participant URL logs
  are avoided at Nginx/Daphne.
- Redis DB 0 cache, DB 1 broker; DB 2 remains reserved for optional Channels.
  Worker response, scheduled dispatch task registration and one Beat verified;
  frozen report delivery semantics remain unchanged.
- Existing #79 preflight and #82 public verifier reused; Ctrl+C exits the public
  verifier 130 with one fixed safe message and no subsequent checks. Runtime verifier adds
  internal container/settings/init/Celery inspection, not duplicate HTTP checks.
- Required CI: lint, test, migration-check, docker-smoke, production-smoke; all
  completed SUCCESS at final implementation HEAD and integrated technical SHA.

## Evidence and bounds

[Gate 4 acceptance](../../testing/gate4-acceptance-verification.md) records exact
PR/merge/CI/jobs, security/failure/static/runtime coverage and limitations.
Integrated technical SHA CI [37064806581](https://github.com/SARD-81/dynamic-forms-platform/actions/runs/37064806581)
completed all five jobs SUCCESS with **502 tests**. Full production build/init,
public checks, separate DB/Redis outages, proxy spoof resistance and cleanup passed.

No previous baseline blob changed. This baseline is engineering acceptance on
dev, not evidence of a provisioned public deployment/TLS certificate or real
SMTP/report transport. Single internal dependency service and Linux TCP behavior
are the accepted timeout context. Real environment secrets, TLS edge and backups
remain operator-owned. Changes require explicit Change Control and a superseding
baseline when foundation semantics change.

## Optional scope

#41 is deferred optional BONUS scope; HTTP reporting remains authoritative.
#95/#96 final operational tasks are completed through PR #100 under the owner's
subsequent closeout instruction. #41 is closed not_planned after explicit deferral.
