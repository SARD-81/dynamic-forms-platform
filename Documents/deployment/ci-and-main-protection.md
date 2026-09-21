# CI and Main Branch Protection

**Gate:** 2G — CI & Repository Protection  
**Status:** IN PROGRESS  
**Target baseline:** BL-FOUNDATION-001

## Required CI checks

The repository defines exactly three required CI job names:

- `lint`
- `test`
- `migration-check`

Repository protection must reference these exact names.

## Workflow triggers

CI runs on:

- every pull request targeting `main`;
- every push to `main`.

## CI runtime

- GitHub-hosted Ubuntu runner
- Python 3.12
- PostgreSQL 16 service container
- Redis 7 Alpine service container
- runtime + dev dependencies from `requirements/dev.txt`

The PostgreSQL and Redis versions in this workflow are CI service choices. The Docker development
topology is frozen separately in GATE 2H.

## Environment contract

GATE 2C intentionally made runtime configuration strict. CI satisfies that contract with disposable
workflow-only values.

No developer, production, or repository secret is required for:

- `DJANGO_SECRET_KEY`
- PostgreSQL credentials
- Redis URLs

These values exist only inside the ephemeral workflow environment.

## Job responsibilities

### lint

```bash
ruff format --check .
ruff check .
```

### test

Runs:

```bash
pytest
```

against PostgreSQL. pytest-django creates its isolated test database using the CI PostgreSQL
service.

### migration-check

Runs:

```bash
python src/manage.py check
python src/manage.py makemigrations --check --dry-run
```

This verifies Django configuration and model/migration drift independently of the test job.

## Main protection target

After the workflow has produced the three check names at least once, `main` must require:

- changes through Pull Requests;
- at least one approving review;
- required status checks:
  - `lint`
  - `test`
  - `migration-check`
- strict/up-to-date status checks;
- force pushes disabled;
- branch deletion disabled.

Administrator enforcement should be enabled when normal peer-review availability is established.
Until collaborator invitations are accepted, any temporary owner exception must stay explicitly
recorded in the governance audit trail and must not be treated as the steady-state policy.

## Protection application

The connected GitHub integration used for repository file work does not expose branch-protection
write administration. Protection is therefore applied with the repository owner's authenticated
GitHub CLI/API after the required check names have appeared on GitHub.

Do not configure required status checks before their first successful/recognized workflow run.
