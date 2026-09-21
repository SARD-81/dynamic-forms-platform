# Contributing

## Branch policy

The authoritative branch model is defined by BL-ARCH-002.

Long-lived branches:

- `main` — stable milestone/release/baseline branch
- `dev` — integration branch for normal ongoing development

Use short-lived Issue-linked branches created from current `dev`, for example:

- `chore/15-docker-development-foundation`
- `feat/22-form-submission`
- `fix/27-process-step-validation`

## Required normal flow

1. Create or select an Issue.
2. Update local `dev`.
3. Create a short-lived branch from `dev`.
4. Implement one coherent concern.
5. Add or update tests.
6. Open a Pull Request targeting `dev`.
7. Wait for CI checks.
8. Obtain peer review when a collaborator is available.
9. Merge only after requirements pass.

## Milestone promotion

`main` is not the target for ordinary feature work.

At an approved milestone:

1. ensure `dev` is green;
2. open a `dev → main` Pull Request;
3. run CI;
4. review the milestone delta;
5. merge into `main`.

## Required CI checks

Stable check names:

- `lint`
- `test`
- `migration-check`

Native GitHub branch protection is currently unavailable for this private repository under the active
plan. That platform limitation does not waive this documented workflow.

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

Business, domain, Service, Selector, and API code must not call `os.getenv()` or otherwise derive
configuration directly from the host environment.

## Cross-platform commands

Makefile targets are optional conveniences only. Documentation must also show direct commands that
work without Make/WSL.

## Frozen baseline changes

A frozen decision may change only through:

1. a `CHG-XXXX` document;
2. explicit impact analysis;
3. approval;
4. a superseding baseline when required.
