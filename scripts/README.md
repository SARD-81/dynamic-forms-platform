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
  --liveness-path /REPLACE_WITH_CONFIRMED_LIVENESS_PATH \
  --readiness-path /REPLACE_WITH_CONFIRMED_READINESS_PATH \
  --static-path /REPLACE_WITH_CONFIRMED_STATIC_ASSET_PATH \
  --timeout 5 \
  --require-all
```

The paths above are placeholders. Obtain the final public routes from Issue #80
and the collected static asset path/public origin from Issue #81.

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
those require the stable #80/#81 interfaces.
