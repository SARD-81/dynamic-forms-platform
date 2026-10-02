# Contributing

## Branch policy

The authoritative branch model is defined by BL-ARCH-002.

Long-lived branches:

- `main` — stable milestone/release/baseline branch
- `dev` — integration branch for normal ongoing development

Use short-lived Issue-linked branches created from current `dev`, for example:

- `chore/78-production-runtime-change-control`
- `feat/81-production-topology`
- `fix/80-readiness-timeout`

## Required normal flow

1. Create or select an Issue.
2. Update local `dev`.
3. Create a short-lived branch from current `dev`.
4. Implement one coherent concern.
5. Add or update tests.
6. Open a Pull Request targeting `dev`.
7. Wait for all applicable CI checks.
8. Resolve or explicitly disposition material automated/manual findings with evidence.
9. Obtain Team Lead Verification.
10. Merge only after the Team Lead explicitly authorizes it.

Independent peer review remains welcome but is optional under the active Gate 4 governance once CHG-0007 is effective. Reviewer requests are not required merely to satisfy process.

Automation/assistant work may prepare and verify PRs but must not merge them unless the repository owner gives an explicit per-merge override to the standing no-assistant-merge rule.

## Milestone promotion

`main` is not the target for ordinary feature work.

At an approved milestone:

1. ensure `dev` is green and the gate's acceptance/freeze requirements are satisfied;
2. open a `dev → main` Pull Request;
3. run all required milestone CI, including gate-specific smoke verification;
4. review the milestone delta and material findings;
5. obtain Team Lead Verification;
6. merge only after explicit Team Lead authorization.

## Required CI checks

Current stable checks:

- `lint`
- `test`
- `migration-check`
- `docker-smoke`

Gate 4 Issue #83 must add the mandatory production-topology verification job `production-smoke` (or an explicitly equivalent name approved by #83/#84). Gate 4 cannot close or promote without that production verification being green.

Native GitHub branch protection is currently unavailable for this private repository under the active
plan. That platform limitation does not waive this documented workflow.

## Review / verification rules

The Team Lead and any optional reviewers verify, as applicable:

- the change matches the linked Issue;
- frozen baselines are not silently changed;
- structural runtime/settings changes have the required Change Record;
- DB constraints from the Constraint Matrix remain real Django/PostgreSQL constraints where applicable;
- Service-only cross-table invariants remain in Services and tests;
- business/service code does **not** read environment variables directly;
- environment access stays in settings/configuration;
- Forms never import Processes;
- migrations are included when models change;
- tests cover important success and failure paths;
- production/runtime/security changes have bounded timeouts and safe failure behavior where applicable;
- no secrets are committed or exposed in logs/responses;
- material automated/manual findings are resolved or explicitly accepted with evidence.

## Gate 4 production control

Gate 4 production-runtime work must respect the approved dependency order:

- #78 / CHG-0006 authorizes production topology before #81 and runtime/foundation changes from #80 may merge;
- #79 provides reusable internal production preflight tooling;
- #82 provides reusable external HTTP/static verification;
- #83 consumes those tools for required automated `production-smoke` verification;
- #84 performs integrated production/security acceptance and baseline/release freeze.

## Environment rule

Settings/configuration may read environment variables.

Business, domain, Service, Selector, API, task, and model code must not call `os.getenv()` or otherwise derive configuration directly from the host environment.

## Cross-platform commands

Makefile targets are optional conveniences only. Documentation must also show direct commands that work without Make/WSL.

## Frozen baseline changes

A frozen decision may change only through:

1. a `CHG-XXXX` document;
2. explicit impact analysis;
3. approval;
4. verified implementation;
5. a superseding baseline when required.
