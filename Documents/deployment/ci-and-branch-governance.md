# CI and Branch Governance

**Historical foundation:** Gate 2G / BL-FOUNDATION-001  
**Current governance extension:** CHG-0005  
**Current closure extension:** Gate 3 Issue #42

## Active CI checks

The current repository workflow defines four stable CI job names:

- `lint`
- `test`
- `migration-check`
- `docker-smoke`

The first three originated in Gate 2. `docker-smoke` is added in Gate 3 closure to verify the complete development runtime after CHG-0003 was applied.

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
- smoke-test `/accounts/login/`, `/api/v1/`, and `/api/schema/?format=json`;
- confirm mandatory Gate 3 API paths exist in the runtime OpenAPI document;
- tear down containers and volumes using an `always()` cleanup step.

## Branch governance — CHG-0005

Normal work:

```text
Issue
→ branch from current dev
→ implementation/tests
→ PR to dev
→ required CI green
→ Team Lead Verification
→ explicit Team Lead merge decision
```

Milestone promotion:

```text
dev
→ PR to main
→ required CI green
→ Team Lead Verification
→ explicit Team Lead merge decision
```

Independent peer `APPROVED` review is optional under CHG-0005. It is not a merge, Definition-of-Done, Issue-closure, or Gate-closure prerequisite and must not be auto-requested merely to satisfy process.

Team Lead Verification remains mandatory before merge and must consider scope, integration state, CI, architecture/frozen-baseline compatibility, migrations, material review findings, security/privacy coverage, and documentation synchronization.

## Native branch protection

GitHub previously returned HTTP 403 for native branch protection on the private repository under the active plan. CHG-0002 / BL-ARCH-002 explicitly accepted documented governance in place of unavailable native protection.

That platform limitation does not waive the Issue → PR → CI → Team Lead Verification workflow.

## Historical governance exceptions

Pull Requests merged before CHG-0005 became effective keep their original audit classification. Governance changes are prospective and do not rewrite history.

The detailed PR-by-PR audit trail is maintained in `Documents/project-control/gate-status.md`.

After CHG-0005 became effective, absence of independent peer approval is not itself a Governance Exception. Material automated/manual findings must still be resolved or explicitly accepted before Team Lead merge authorization.

## Gate 3 closure rule

The #42 closure-candidate PR must not mark Gate 3 CLOSED or invent a freeze SHA before merge. After the Team Lead reviews and merges that candidate, the exact merged `dev` SHA is used in a separate documentation-only freeze PR for `BL-FOUNDATION-002` and `BL-APPLICATION-001`.

The final `dev → main` milestone is a separate PR and must pass the same active CI/Team Lead Verification gates before the Team Lead chooses to merge it.
