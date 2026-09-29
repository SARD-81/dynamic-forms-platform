# CI and Branch Governance

**Gate:** 2G — CI & Repository Governance  
**Status:** COMPLETED / PASSED  
**Target baseline:** BL-FOUNDATION-001  
**Architecture baseline:** BL-ARCH-002

## Required CI checks

The repository defines exactly three stable CI job names:

- `lint`
- `test`
- `migration-check`

## Workflow triggers

CI runs on:

- Pull Requests targeting `dev`;
- Pull Requests targeting `main`;
- pushes to `dev`;
- pushes to `main`.

## CI runtime

- GitHub-hosted Ubuntu runner
- Python 3.12
- PostgreSQL 16 service container
- Redis 7 Alpine service container
- runtime + dev dependencies from `requirements/dev.txt`

CI satisfies the strict environment contract with disposable workflow-only values. No developer or
production secret is required.

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

### migration-check

```bash
python src/manage.py check
python src/manage.py makemigrations --check --dry-run
docker compose --env-file .env.example config --quiet
```

## Runtime verification

The final GATE 2G workflow head passed all three jobs.

```text
lint             success
test             success
migration-check  success
overall CI       success
```

PostgreSQL and Redis service containers initialized successfully.

## Branch governance

Normal work:

```text
Issue → branch from dev → PR to dev → review → CI → merge to dev
```

Milestone promotion:

```text
dev → PR to main → review → CI → merge to main
```

## Native branch protection

GitHub returned HTTP 403 for branch protection on the current private repository because the active
plan does not provide that feature.

The repository remains private and native branch protection is explicitly not a Gate 2 exit
requirement under CHG-0002 / BL-ARCH-002.

This platform limitation does not waive the documented PR/review/CI workflow.


## Governance exceptions

Peer review remains the default requirement for GATE 3 Pull Requests. A merge that occurs without an
independent approval is an explicit governance exception and must not be represented as if the normal
review requirement was satisfied.

For every such exception:

- record the affected PR and resulting merge commit in the project governance audit trail;
- record that independent peer approval was absent at merge time;
- do not inherit or reuse an approval from an earlier or related PR;
- keep CI/test evidence separate from review evidence: green CI does not substitute for peer approval;
- return to the normal peer-review workflow for subsequent Pull Requests.

This exception mechanism is an audit rule, not an alternative default workflow.
