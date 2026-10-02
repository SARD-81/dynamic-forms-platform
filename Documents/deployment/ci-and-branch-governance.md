# CI and Branch Governance

**Historical foundation:** Gate 2G / BL-FOUNDATION-001  
**Gate 3 governance:** CHG-0005  
**Gate 4 governance:** CHG-0007 (effective only after its transition PR merges)  
**Current Gate:** Gate 4 — Production Readiness, Release Hardening & Bonus Enhancements

## Active CI checks

The current repository workflow defines five stable required jobs:

- `lint`
- `test`
- `migration-check`
- `docker-smoke`
- `production-smoke`

The first three originated in Gate 2. `docker-smoke` was added in Gate 3 closure to verify the complete development runtime after CHG-0003 was applied.

Gate 4 Issue #83 adds `production-smoke`. All five jobs must complete successfully on the final PR HEAD for Gate 4 closure and `dev → main` promotion. Pending, skipped, cancelled or incomplete jobs do not count. GitHub Actions Check Runs are the evidence; a legacy combined status marked pending with zero status contexts is not a failed Actions job.

## Workflow triggers

CI runs on Pull Requests and pushes targeting `dev` or `main` according to `.github/workflows/ci.yml`.

## Current job responsibilities

### lint

```bash
ruff format --check .
ruff check .
```

### test

```bash
pytest
```

The suite uses `config.settings.test` and exercises PostgreSQL-backed constraints plus deterministic test cache behavior.

### migration-check

```bash
python src/manage.py check
python src/manage.py makemigrations --check --dry-run
docker compose --env-file .env.example config --quiet
```

### docker-smoke

From a clean runner the job builds and starts the full five-service development topology, waits for Django readiness, verifies `web`, `postgres`, `redis`, `celery-worker`, and `celery-beat`, checks Celery worker/task registration, smoke-tests critical HTML/API/OpenAPI routes, and always tears down containers/volumes.

This job validates the development topology. It does not replace the Gate 4 production-topology verification owned by #83.

### production-smoke

The required job validates/builds/starts the real seven-role production topology
from a clean runner, checks one-shot init completion, production settings, applied
migrations, collected project/admin assets, internal ports/dependency health,
worker response/task registration and Beat state. It reuses #79 preflight and #82
HTTP/static verification with `--require-all`; no competing HTTP verifier exists.

Additional acceptance covers exact project CSS bytes, home/login/API/OpenAPI,
private/source-file denial, separate PostgreSQL/Redis outages returning bounded
503 while liveness remains 200, and secure redirects despite forged forwarded
protocol input. The HTTP smoke override is explicit; secure cookies remain on.
All waits and job execution are finite, CI-only credentials are disposable,
no report delivery task is invoked, and teardown always removes this job's own
containers/volumes. The temporary #81 production-candidate workflow is removed.

## Gate 4 governance — CHG-0007

CHG-0005 remains a historical Gate 3 governance record and is not silently extended to Gate 4.

After the CHG-0007 transition PR is explicitly reviewed and merged by the Team Lead, normal Gate 4 work uses:

```text
Issue
→ branch from current dev
→ implementation/tests
→ PR to dev
→ required CI green
→ Team Lead Verification
→ explicit Team Lead merge decision
```

Milestone promotion uses:

```text
dev
→ PR to main
→ all required Gate 4 CI green
→ Team Lead Verification
→ explicit Team Lead merge decision
```

Independent peer `APPROVED` review is optional under CHG-0007 and must not be auto-requested merely to satisfy process.

Team Lead Verification remains mandatory and must consider scope, integration state, CI, architecture/frozen-baseline compatibility, migration intent, material review findings, security/privacy/runtime coverage, and documentation synchronization.

## CHG-0007 transition handling

The CHG-0007 PR is the one-time transition from the provisional Gate 4 peer-review rule to Team Lead Verification.

It may reach merge readiness without independent peer approval because the Team Lead explicitly authorized the governance transition. CHG-0007 becomes effective only after that PR is merged to `dev` by the Team Lead.

PR #88 / Issue #79 merged before CHG-0007 became effective and had no independent peer `APPROVED` review. Under the provisional Gate 4 rule it remains a one-time historical Governance Exception; history is not rewritten retroactively.

## Production-runtime authorization boundary

Gate 4 governance approval is separate from runtime/foundation authorization.

- #78 / CHG-0006 must authorize production topology/runtime/security changes before #81 is merged;
- the runtime/settings portion of #80 must not merge before #78 / CHG-0006;
- #79 production preflight is already complete because it adds verification tooling rather than topology;
- #82 may develop reusable external verification tooling independently and finalize against stable #80/#81 public contracts;
- #83 must reuse #79/#82 tooling rather than duplicating equivalent checks in workflow YAML.

## Native branch protection

Native GitHub branch protection was previously unavailable for this private repository under the active plan. CHG-0002 / BL-ARCH-002 accepted documented governance in place of unavailable native protection.

That platform limitation does not waive Issue → PR → CI → Team Lead Verification → explicit merge decision.

## Historical governance

Historical PRs retain the classification applicable at their merge time. Governance changes are prospective and never rewrite history.

Detailed current gate/audit status is maintained in `Documents/project-control/gate-status.md`.
