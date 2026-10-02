# CI and Branch Governance

**Historical foundation:** Gate 2G / BL-FOUNDATION-001  
**Gate 3 governance extension:** CHG-0005  
**Gate 4 governance extension:** CHG-0007 (effective after transition PR merge)

## Active CI checks

The current repository workflow defines four stable CI job names:

- `lint`
- `test`
- `migration-check`
- `docker-smoke`

The first three originated in Gate 2. `docker-smoke` was added in Gate 3 closure to verify the complete development runtime after CHG-0003 was applied.

Gate 4 Issue #83 must add a stable `production-smoke` job, or an explicitly equivalent required job named by #83/#84. Gate 4 cannot close or promote without deterministic automated production-topology verification.

## Workflow triggers

CI runs on:

- Pull Requests targeting `dev`;
- Pull Requests targeting `main`;
- pushes to `dev`;
- pushes to `main`.

## CI runtime

- GitHub-hosted Ubuntu runner;
- Python 3.12 for lint/test/migration jobs;
- PostgreSQL 16 service container where required;
- Redis 7 Alpine service container where required;
- runtime + dev dependencies from `requirements/dev.txt`;
- Docker Compose for clean full-topology smoke verification.

Workflow-only values satisfy the settings contract. No developer or production secret is required.

## Job responsibilities

### lint

```bash
ruff format --check .
ruff check .
```

### test

```bash
pytest
```

The full suite uses `config.settings.test` and exercises PostgreSQL-backed database constraints plus deterministic local-memory cache behavior where configured.

### migration-check

```bash
python src/manage.py check
python src/manage.py makemigrations --check --dry-run
docker compose --env-file .env.example config --quiet
```

### docker-smoke

From a clean runner:

- copy `.env.example` to a disposable `.env` and replace required placeholders;
- build and start the full five-service development topology;
- wait for the containerized Django API to become ready;
- verify `web`, `postgres`, `redis`, `celery-worker`, and `celery-beat` are running;
- run Celery worker `inspect ping`;
- verify scheduled-report task registration;
- smoke-test critical HTML/API/OpenAPI routes;
- confirm mandatory Gate 3 API paths exist in the runtime OpenAPI document;
- tear down containers and volumes using an `always()` cleanup step.

## Gate 4 production verification path

Gate 4 adds production-specific verification without replacing `docker-smoke`.

- #79 provides the internal `production_preflight` management command;
- #80 provides stable liveness/readiness/logging contracts after CHG-0006 authorization;
- #81 provides the production ASGI/Nginx/collectstatic topology;
- #82 provides a reusable external HTTP/static verifier;
- #83 wires those reusable tools into mandatory `production-smoke` CI;
- #84 reuses the same path for final production/release acceptance.

The production workflow must not duplicate application/database/cache checks that already belong to #79 or duplicate external HTTP assertions that belong to #82.

## Branch governance — Gate 4 / CHG-0007

CHG-0005 remains the historical Gate 3 governance record and is not silently extended.

Once CHG-0007's transition PR is manually merged to `dev`, Gate 4 normal work uses:

```text
Issue
→ branch from current dev
→ implementation/tests
→ PR to dev
→ required CI green
→ material findings resolved or explicitly accepted with evidence
→ Team Lead Verification
→ explicit Team Lead merge decision
```

Milestone promotion:

```text
dev
→ PR to main
→ all required CI including production-smoke
→ material findings resolved/accepted
→ Team Lead Verification
→ explicit Team Lead merge decision
```

Independent peer `APPROVED` review is optional under CHG-0007. It is not a merge, Definition-of-Done, Issue-closure, Gate-closure, or milestone prerequisite and must not be auto-requested merely to satisfy process.

Team Lead Verification remains mandatory and must consider scope, integration state, CI, architecture/frozen-baseline compatibility, migrations, production/runtime/security implications, material review findings, and documentation synchronization.

Automation/assistant work may prepare branches/PRs, implement scoped changes, inspect CI, fix findings and prepare evidence. It must not merge Gate 4 PRs unless the repository owner gives an explicit per-merge override to the standing no-assistant-merge rule.

## Native branch protection

GitHub previously returned HTTP 403 for native branch protection on the private repository under the active plan. CHG-0002 / BL-ARCH-002 explicitly accepted documented governance in place of unavailable native protection.

That platform limitation does not waive the Issue → PR → CI → Team Lead Verification workflow.

## Historical governance classification

Governance changes are prospective and do not rewrite history.

- PRs merged before CHG-0005 keep their Gate 3-era classification.
- PR #88 / Issue #79 merged after Gate 4 kickoff planning had restored mandatory peer review but before CHG-0007 became effective; it therefore remains a historical Gate 4 Governance Exception because no independent peer `APPROVED` review was present.
- PR #85 is superseded rather than merged because its kickoff/control branch became stale after #79 merged and because its governance text no longer matches the repository owner's explicit Gate 4 decision.
- draft PR #86 must be refreshed/re-scoped against current `dev` or superseded.
- PR #87 may remain open but runtime/foundation changes must not merge before #78 / CHG-0006 is effective.

The detailed PR-by-PR audit trail is maintained in `Documents/project-control/gate-status.md`.

## Gate 4 closure rule

#84 must not invent a technical freeze SHA or mark Gate 4 CLOSED before mandatory implementation and integrated production verification actually merge to `dev`.

After the verified mandatory state is established:

1. record the exact `dev` technical freeze point;
2. freeze justified superseding baseline/release documents (`BL-FOUNDATION-003` and `BL-RELEASE-001` when warranted);
3. mark Gate 4 CLOSED/FROZEN on `dev`;
4. open a separate `dev → main` milestone PR;
5. require all active CI including `production-smoke` plus Team Lead Verification;
6. merge only after explicit Team Lead decision;
7. finalize tracker #77 housekeeping.
