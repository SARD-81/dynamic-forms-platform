## Production HTTP/static verifier

Run the standalone verifier with Python 3.12. No third-party dependency is required.

### Core checks

```bash
python scripts/verify_production.py --base-url https://your-host.example --timeout 5
```

This checks login, API root and schema. Missing health/static paths are reported as
SKIP, and the summary explicitly identifies incomplete coverage.

### Complete acceptance checks

```bash
python scripts/verify_production.py \
  --base-url https://your-host.example \
  --liveness-path /health/live/ \
  --readiness-path /health/ready/ \
  --static-path /static/core/app.css \
  --timeout 5 \
  --require-all
```

These are the stable #80/#81 public routes. Set the base URL to your deployed
origin. `--static-sha256 <64-hex-digest>` optionally checks that the selected asset
has the expected bytes (at most 2 MiB); only this opt-in check reads a response body,
and that body is never printed. `--header Name:value` supplies an optional request
header, used by CI to test that forged forwarded protocol is overwritten by Nginx.
Invalid header/digest arguments do not expose their supplied values in diagnostics.

CI and final acceptance should use --require-all.

Each check expects HTTP 200 by default. Override an expected status only to match
the agreed endpoint contract, for example --readiness-status 204.

Login, API and schema paths are also configurable. See --help.

### Exit codes and diagnostics

- 0: all selected checks passed; inspect the summary for partial coverage.
- 1: at least one HTTP check failed.
- 2: invalid command-line arguments.

Redirects are not followed. Response bodies, full URLs and exception messages
are not printed. TLS certificate verification remains enabled.

### Timeout behavior

--timeout supplies a positive finite timeout to urllib's blocking network
operations. Checks run sequentially without application-level retries.

This is not a guaranteed total wall-clock deadline: DNS resolution and multiple
network operations may exceed the configured value. CI should also configure an
overall job timeout.

### Relationship to production_preflight

Issue #79's Django production_preflight command checks internal application
settings and database/cache connectivity.

This verifier checks the external HTTP/static boundary. It does not repeat
database/cache probes or execute production_preflight automatically.

Deployment/CI orchestration should run the internal preflight in the application
container and invoke this verifier against the public origin, checking both exit
statuses.

### Tests

```bash
python -m pytest tests/test_verify_production.py -q
```

The tests include a local HTTP server and standalone CLI execution. They do not
prove that the final production proxy, health routes or static deployment work;
those require the production-smoke job against the real #80/#81 topology.

## Production runtime verifier

`verify_production_runtime.py` checks only Compose/container/runtime internals and
calls the existing production_preflight command. It leaves every public HTTP
assertion in verify_production.py. Raw config/inspect output is withheld because
it includes environment secrets.

```bash
python scripts/verify_production_runtime.py --env-file .env.production --project-name dynamic-forms-production
```

See the [production guide](../Documents/deployment/production.md) for start/stop,
static volumes, TLS-edge trust, safe local smoke and destructive smoke-only cleanup.
