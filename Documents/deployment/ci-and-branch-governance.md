# CI and Branch Governance

**Gate:** 2G — CI & Repository Governance  
**Status:** IN PROGRESS  
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

## Environment contract

GATE 2C intentionally made runtime configuration strict. CI satisfies that contract with disposable
workflow-only values.

No developer or production secret is required.

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
```

## First runtime verification

The first CI run on PR #14 completed successfully:

```text
lint             success
test             success
migration-check  success
overall CI       success
```

PostgreSQL and Redis service containers initialized successfully.

## Branch governance

Normal work uses:

```text
Issue → branch from dev → PR to dev → review → CI → merge to dev
```

Milestone promotion uses:

```text
dev → PR to main → review → CI → merge to main
```

## Native branch protection

An attempt to enable GitHub branch protection on the private repository returned HTTP 403 because
the current GitHub plan does not provide that feature for this repository.

The project owner explicitly chose to keep the repository private and continue without native branch
protection.

This is a platform-plan limitation, not a CI failure. Project governance still prohibits normal
direct development on `main` and `dev`.

See CHG-0002 and BL-ARCH-002.
