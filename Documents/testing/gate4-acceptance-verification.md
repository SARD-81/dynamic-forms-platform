# Gate 4 acceptance verification

**Status:** ACCEPTED / FROZEN ON DEV — milestone promotion pending  
**Verified:** 2026-10-02 UTC  
**Technical freeze point:** `dev@f62cce74c67053ec2e2af06fb3ed75bd20a3ca00`  
**Issues:** #77 / #84  
**Baselines:** BL-FOUNDATION-003 and BL-RELEASE-001 at the same implementation SHA

## Evidence boundary

The SHA above was obtained from live dev AFTER the verified Squash merges for
#80/#81/#83, final #95/#96 and acceptance corrections #102. A fresh push CI run tested that exact implementation state. The later
closure documentation merge activates acceptance on dev and is not substituted
for the technical freeze point. Acceptance does not assert a public hosting
provider, certificate or real mail/report destination has been provisioned.

## Implementation and CI evidence

| Scope | PR / final HEAD | Verified dev merge | CI evidence |
| --- | --- | --- | --- |
| #80 | #87 / `85735111f52bbccd492512144dc65db700994c62` | `a8bd8649ef4e07fb4cc44bb9f07b1bae187b9506` | [37060313235](https://github.com/SARD-81/dynamic-forms-platform/actions/runs/37060313235): four jobs SUCCESS, 467 tests |
| #81 | #97 / `0ae8ac7575ced7f3a73d6ddef01276ccb5273e41` | `e4a563ae0f63a720f045178113a5a9a271da4465` | [37061108231](https://github.com/SARD-81/dynamic-forms-platform/actions/runs/37061108231): four jobs SUCCESS, 476 tests; [37061108305](https://github.com/SARD-81/dynamic-forms-platform/actions/runs/37061108305): real topology candidate SUCCESS |
| #83 | #98 / `948066bebf71f26e9d1cc1ccec383704ffaa8b8f` | `2a5cea20f5cf3237645f35c8e89dab3665d77ac7` | [37062061257](https://github.com/SARD-81/dynamic-forms-platform/actions/runs/37062061257): all five jobs SUCCESS, 487 tests |
| #95/#96 | #100 / `3c6e1c267a7092a9b0d8bd1cb8eb2e8b0205c386` | `df5609b17f8238661b7cc464228f5837ce7f4537` | [37064542544](https://github.com/SARD-81/dynamic-forms-platform/actions/runs/37064542544): all five jobs SUCCESS, 502 tests |
| Final correction | #102 / `64b12b69606fa86b22e98071cecf15edb11dace4` | `f62cce74c67053ec2e2af06fb3ed75bd20a3ca00` | [37066499042](https://github.com/SARD-81/dynamic-forms-platform/actions/runs/37066499042): all five jobs SUCCESS, 509 tests |
| Integrated dev | exact technical freeze SHA above | same SHA | [37066868098](https://github.com/SARD-81/dynamic-forms-platform/actions/runs/37066868098): all five jobs SUCCESS, 509 tests |

Exact integrated dev jobs: lint 111036822043; test 111036821978;
migration-check 111036822082; docker-smoke 111036822163;
production-smoke 111036821814. Check Runs completed SUCCESS; no pending/cancelled
job was counted as green. Empty legacy status contexts were not treated as a
failed Actions check. Final closure and milestone PR evidence is maintained in
live #84/#77 after each action, rather than guessing future PR/merge identifiers.

## Fresh integrated audit

The final dev tree and critical production/settings/health/logging/CI/verifier
files were fetched at the exact freeze SHA. The mandatory implementation diff
contains only the audited production, operational, verification, test and related
documentation files. Existing domain models/services/selectors, migrations,
templates and application contracts are unchanged. All six pre-existing frozen
baseline blobs match their starting hashes. There is no BL-APPLICATION-002.

The tree contains no tracked .env/.env.production, generated cache/bytecode,
SQLite database or build junk. Git history searches for the real environment file
paths returned no commits. The source review and credential-pattern scan found
no committed real secrets; examples and CI contain intentional placeholders.
Application business code has no direct host environment reads. Configuration
ownership remains in src/config. No new runtime dependency is introduced.

## Acceptance matrix

| Boundary | Evidence and accepted result |
| --- | --- |
| Production settings | DEBUG=False; explicit required hosts/origins; secure session/CSRF cookies; SSL redirect true by default; development/test/production imports and host/proxy tests pass |
| Proxy trust | Daphne has no host port. Nginx sets Host, overwrites protocol, strips client Forwarded/X-Forwarded-Host, replaces forwarded IP; opt-in SECURE_PROXY_SSL_HEADER only for trusted ingress. HTTPS mode startup requires loopback and operator-managed TLS edge |
| HTTPS behavior | Public smoke with forged X-Forwarded-Proto:https still returns 301 when redirect enabled; local false override is explicit and cookies stay secure |
| Initialization | Clean Compose config/build/up succeeded; init exited 0 after migrate, collectstatic and production_preflight. Applied migration graph has no pending nodes; failing init blocks downstream startup by dependency contract |
| Runtime | Seven exact roles; production settings active; Daphne command verified, no runserver; only Nginx host port; no bind mounts; PostgreSQL/Redis/web healthy; worker/Beat running |
| Scheduled reports | Worker ping returned pong; apps.reports.tasks.dispatch_due_report_subscriptions registered; Beat process present; frozen hourly dispatch/delivery tests pass; no delivery task invoked by smoke |
| Static | STATIC_ROOT=/app/staticfiles, init writable and web/Nginx read-only shared volume; project/admin assets collected; exact project CSS SHA256 verified via Nginx; admin CSS publicly reached; preserved-volume update seeds stale future-dated CSS and an obsolete asset, reruns actual init, verifies restored exact CSS hash and obsolete asset 404 |
| Exposure | /static/.env, /static/config/settings/production.py, /.env and /src/manage.py return 404 through Nginx; static root contains only collected assets, no private/source directory mount |
| Public behavior | Home, login, API root, OpenAPI, liveness, readiness and static routes succeed through Nginx using reusable #82 verifier with --require-all |
| Dependency failure | Separate stopped PostgreSQL and Redis produce readiness 503 within public verifier timeout 5s while liveness remains 200; dependencies restored and readiness reverified 200 |
| Probe reliability | Silent TCP peers exercise real connect/read bounds; disposable DB probe options leave business sessions unchanged; UUID cache keys avoid concurrent collisions; timeout configuration invalid inputs fail safely |
| Failure privacy/logging | Generic readiness JSON omits hosts/passwords/URLs. Parameterized/quoted/bytes logs, exceptions, multi-handler tracebacks and stack text redact passwords, Bearer/API/OTP, SMTP user/password, access/resume secrets, both URI username/password (including email usernames) and query tokens |
| Log transport | Container console Django/Celery handlers retained; Celery does not hijack root; Nginx access omits args/referer; unsafe raw Nginx request errors and Daphne access logging disabled |
| Tool reuse | #79 preflight used in init and runtime verification; #82 owns public HTTP/static assertions; #83 supplies finalized inputs, not a competing verifier |
| Regression | 509 tests pass, including auth/OTP/participant/security/form/process/report contracts; Ruff format/lint, Django check and migration drift pass; full five-service Gate 3 docker-smoke and mandatory production-smoke succeed |

The integrated production job printed PASS for config/runtime, production
settings/applied migrations/collected assets, Production preflight passed, worker
response/registration and every configured public check. Outage phases produced
503, secure redirect phase 301 and restored phase 200. Teardown completed SUCCESS
and removed the job's disposable containers/volumes.

## Findings and disposition

PR #99 was rejected at pre-merge scope verification for an incomplete base tree,
closed unmerged and replaced by clean PR #100. Its superseded branch was restored
to the complete dev snapshot by a non-destructive fast-forward commit. No such
deletions reached dev or the final freeze.

Late automated findings on #87/#97 and final #102 were resolved through the
verified final acceptance correction before baseline activation. Material findings
were fixed and reverified: stale readiness timeout
ownership, probe session mutation risk, silent dependency hangs, quoted/bytes and
SMTP/userinfo log secrets, unsafe raw request logging, narrow proxy trust,
non-empty/empty-password URI username disclosure, quadratic log-key/URI matching,
stale collected assets on preserved volumes, real-CSRF 403 instead of the health 405 method
contract (fixed only on public method-guarded health views), Docker upstream DNS
changes on web replacement, static verification and private
file exposure coverage. No material unresolved review thread remained. Teammate
PR #87 history was preserved; no force push was used. Baseline files were not
rewritten and tests were not weakened.

Local Ruff and focused operational/verifier tests passed. The Work terminal lacked
Docker and local PostgreSQL/Redis; actual full tests/container acceptance ran on
clean GitHub runners. GitHub Actions, rather than a local unexecuted command, is
the authoritative production and merge evidence.

## Limits and operating assumptions

PostgreSQL connect_timeout applies per resolved host/address; the verified Linux
Compose path uses one internal service. External DNS/multi-host deployments need
their own latency acceptance. Regex log redaction covers named sensitive patterns,
not arbitrary unlabeled private strings; never log raw answers/cookies/bodies.

TLS edge/certificates, real secrets/SMTP destinations, backups and deployment
operations are operator responsibilities documented in the production guide.
Smoke deliberately verifies public reachability over explicit local HTTP and does
not send real email/API reports; frozen delivery/auth correctness is covered by
tests, not a real external transport or browser TLS session. Existing dependency
ranges and image tags are retained; this gate does not add a deployment provider
or a new dependency-locking scheme.

## Freeze, optional scope and promotion

BL-FOUNDATION-003 supersedes only the active engineering/runtime foundation;
BL-RELEASE-001 accepts the same exact verified SHA. BL-APPLICATION-001 remains
application authority. Closure on dev requires green final closure PR CI and its
explicit authorized Squash merge. Activation evidence is recorded in #84/#77.

**#41 is deferred optional BONUS scope; HTTP reporting remains authoritative.**
#95/#96 final code tasks are completed through PR #100, including GET/HEAD
status parity, empty HEAD bodies, unsupported methods under enforced CSRF, safe cancellation and real
SIGINT/exit-130 tests. #41 is closed not_planned without claiming implementation.

The separate dev-to-main milestone must have all five checks completed SUCCESS
and remain open for manual Team Lead merge. This Work session does not authorize
main promotion. #84 and Tracker #77 stay open until promotion satisfies their DoD.
