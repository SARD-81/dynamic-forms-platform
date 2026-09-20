# Contributing

## Branch policy

`main` is the only long-lived branch.

Use short-lived branches named from an Issue, for example:

- `chore/1-repository-governance-bootstrap`
- `feat/12-form-submission`
- `fix/27-process-step-validation`

## Required flow

1. Create or select an Issue.
2. Create a branch from current `main`.
3. Implement one coherent concern.
4. Add or update tests.
5. Open a Pull Request.
6. Wait for required CI checks.
7. Obtain at least one peer approval once repository protection is enabled.
8. Merge only after all requirements pass.

## Review rules

Reviewers must verify:

- the change matches the linked Issue;
- frozen baselines are not silently changed;
- DB constraints from the Constraint Matrix are real Django/PostgreSQL constraints where applicable;
- Service-only cross-table invariants remain in Services and tests;
- business/service code does **not** read environment variables directly;
- environment access stays in settings/configuration;
- Forms never import Processes;
- migrations are included when models change;
- tests cover important success and failure paths;
- no secrets are committed.

## Environment rule

Settings/configuration may read environment variables.

Business, domain, Service, Selector, and API code must not call `os.getenv()` or otherwise derive configuration directly from the host environment.

## Cross-platform commands

Makefile targets are optional conveniences only. Documentation must also show direct commands that work without Make/WSL.

## Frozen baseline changes

A frozen decision may change only through:

1. a `CHG-XXXX` document;
2. explicit impact analysis;
3. approval;
4. a superseding baseline when required.
