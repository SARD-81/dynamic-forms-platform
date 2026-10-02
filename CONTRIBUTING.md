# Contributing

## Branch policy

The authoritative branch model is defined by BL-ARCH-002.

Long-lived branches:

- `main` — stable milestone/release/baseline branch
- `dev` — integration branch for normal ongoing development

Use short-lived Issue-linked branches created from current `dev`.

## Required normal flow

1. Create or select an Issue.
2. Update local `dev`.
3. Create a short-lived branch from current `dev`.
4. Implement one coherent concern.
5. Add or update tests.
6. Open a Pull Request targeting `dev`.
7. Wait for all required CI checks.
8. Resolve or explicitly disposition material automated/manual findings.
9. Complete Team Lead Verification.
10. Merge only after explicit Team Lead authorization.

Independent peer review is welcome but, under effective CHG-0007 for Gate 4, it is optional rather than a mandatory merge/Definition-of-Done gate. Reviewers must not be auto-requested merely to satisfy process.

## Milestone promotion

`main` is not the target for ordinary feature work.

At an approved milestone:

1. ensure `dev` is fully green;
2. open a `dev → main` Pull Request;
3. run all required milestone CI;
4. review the complete milestone delta and frozen-baseline/release evidence;
5. complete Team Lead Verification;
6. merge only after explicit Team Lead authorization.

Gate 4 promotion requires all five active checks, including `production-smoke` introduced by #83.

## Current required CI checks

- `lint`
- `test`
- `migration-check`
- `docker-smoke`
- `production-smoke`

All five must complete successfully on the final PR HEAD. Pending, cancelled or skipped checks are insufficient.

## Review / Team Lead Verification rules

Verify as applicable:

- change matches the linked Issue;
- frozen baselines are not silently changed;
- structural runtime/foundation changes have approved Change Control first;
- DB constraints are real Django/PostgreSQL constraints where required;
- Service-only cross-table invariants remain in Services and tests;
- business/service code does not read environment variables directly;
- environment access stays in settings/configuration;
- Forms never import Processes;
- migrations are included and intentional when models change;
- important success/failure/security paths are tested;
- material Codex/manual findings are resolved or explicitly accepted with evidence;
- no secrets are committed;
- documentation/contracts are synchronized when behavior or operating procedures change.

## Gate 4 control boundaries

- #78 / CHG-0006 is effective through PR #91 and authorized the verified #80/#81 runtime changes.
- #79 production preflight is complete and supplies a reusable internal verification interface.
- #82 owns reusable external HTTP/static verification without defining Nginx/Compose architecture.
- #83 supplies the mandatory production-smoke job and reuses #79/#82 tooling.
- #41 is deferred optional BONUS scope; HTTP reporting remains authoritative.
- #95/#96 final finishing tasks are complete; no contributor task remains open.
- Gate 4 is CLOSED/FROZEN at the recorded technical SHA; PR #103 records milestone promotion.
- The owner subsequently authorized the assistant to merge PR #103 only after a fresh complete requirements audit and all five green checks. No auto-merge is allowed.
- #84 and #77 close only after the resulting main commit is verified.

## Environment rule

Settings/configuration may read environment variables.

Business, domain, Service, Selector, API, task and model code must not call `os.getenv()` or otherwise derive configuration directly from the host environment.

## Cross-platform commands

Makefile targets are optional conveniences only. Documentation must also show direct commands that work without Make/WSL.

## Frozen baseline changes

A frozen decision may change only through:

1. a `CHG-XXXX` document;
2. explicit impact analysis;
3. approval;
4. applied/verified implementation;
5. a superseding baseline when required.

