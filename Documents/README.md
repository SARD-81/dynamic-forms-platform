# Project Documentation

This directory is the version-controlled engineering record for the project.
The root [README](../README.md) explains how to use, run and verify the application.

## Current release state

Gate 4 is **CLOSED / FROZEN** at technical freeze point
`f62cce74c67053ec2e2af06fb3ed75bd20a3ca00`, after #80/#81/#83, #95/#96 and final #102
were integrated and verified. [Milestone PR #103](https://github.com/SARD-81/dynamic-forms-platform/pull/103)
records the final promotion state, CI and main commit; #84 and Tracker #77 close
after verified promotion. Later documentation commits do not replace the technical freeze point.

- [Gate status](project-control/gate-status.md)
- [Gate 4 execution and closeout](project-control/gate4-execution-plan.md)
- [Gate 4 acceptance evidence](testing/gate4-acceptance-verification.md)
- [Final project requirements and contract audit](testing/final-project-requirements-audit.md)
- [CHG-0006: applied production runtime authorization](project-control/change-records/CHG-0006.md)
- [CHG-0007: effective Gate 4 governance](project-control/change-records/CHG-0007.md)
- [Decision log](project-control/decision-log.md)

## Active baselines

| Baseline | Authority |
| --- | --- |
| [BL-ARCH-002](project-control/baselines/BL-ARCH-002.md) | Architecture |
| [BL-DATA-002](project-control/baselines/BL-DATA-002.md) | Domain/data |
| [BL-FOUNDATION-003](project-control/baselines/BL-FOUNDATION-003.md) | Verified development and production engineering/runtime foundation |
| [BL-APPLICATION-001](project-control/baselines/BL-APPLICATION-001.md) | Frozen mandatory application semantics; unchanged by Gate 4 |
| [BL-RELEASE-001](project-control/baselines/BL-RELEASE-001.md) | Gate 4 production/release acceptance at the same technical SHA |

BL-FOUNDATION-003 supersedes BL-FOUNDATION-002 for the active foundation.
[BL-FOUNDATION-002](project-control/baselines/BL-FOUNDATION-002.md) and
[BL-FOUNDATION-001](project-control/baselines/BL-FOUNDATION-001.md) remain immutable
historical records. No BL-APPLICATION-002 is created: operational endpoints and
runtime hardening do not change frozen form/process/report semantics.

## Operating and verifying

- [Environment contract](deployment/environment-contract.md)
- [Production deployment, HTTPS trust, start/update/cleanup](deployment/production.md)
- [Health, dependency bounds and logging](deployment/health-and-logging.md)
- [Docker development](deployment/docker-development.md)
- [CI and branch governance](deployment/ci-and-branch-governance.md)
- [Verification scripts](../scripts/README.md)
- [Quality and test foundation](testing/quality-test-foundation.md)

The production topology and mandatory `production-smoke` reuse #79
`production_preflight` and #82 `scripts/verify_production.py`. Neither smoke
verification path sends real mail or external reports.

## Application and historical records

- [API conventions](api/api-conventions.md)
- [Authentication and email OTP](architecture/authentication-otp-contract.md)
- [Participant access/cache](architecture/participant-access-cache-contract.md)
- [Shared presentation templates](architecture/presentation-template-contract.md)
- [Rendered ERD](database/erd.svg) and [source](database/erd.nomnoml)
- [Gate 3 execution plan](project-control/gate3-execution-plan.md)
- [Gate 3 acceptance](testing/gate3-acceptance-verification.md)
- [Foundation bootstrap verification](deployment/foundation-bootstrap-verification.md)

## Remaining work and change control

#41 is deferred optional BONUS scope; HTTP reporting remains authoritative.
The two final code tasks #95/#96 are completed: health HEAD support and safe
verifier interruption. #41 is closed not_planned following the explicit deferral. Later changes require their own Issue, verification and Team Lead
merge decision. Frozen records are superseded through explicit change control,
never rewritten in place.
