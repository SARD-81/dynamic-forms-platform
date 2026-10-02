# BL-RELEASE-001 — Gate 4 release acceptance

**Status:** FROZEN / ACCEPTED ON DEV — milestone promotion pending  
**Verified:** 2026-10-02 UTC  
**Technical acceptance SHA:** `dev@f62cce74c67053ec2e2af06fb3ed75bd20a3ca00`  
**Foundation:** BL-FOUNDATION-003 at the same exact SHA  
**Application:** BL-APPLICATION-001 (unchanged)  
**Architecture/data:** BL-ARCH-002 / BL-DATA-002  
**Tracker / closeout:** #77 / #84, open until main promotion

## Accepted release state

All mandatory Gate 4 technical work (#78–#83) and final #95/#96 code tasks are
integrated and verified. This
baseline records production-readiness acceptance for the same implementation
state as BL-FOUNDATION-003; there is no intentionally different acceptance SHA.
The later documentation merge activates both baselines on dev without changing
the Technical Freeze Point. Main promotion is a separate milestone action.

The release provides production settings, Daphne serving, one Nginx public HTTP/
static boundary, deterministic migrate/collectstatic/preflight initialization,
internal PostgreSQL/Redis/Celery worker/Beat, bounded health behavior and safe
logging. Development runtime and frozen mandatory application semantics remain
regression-green. #79/#82 tooling is reused by required production-smoke.

## Mandatory acceptance evidence

[Gate 4 acceptance verification](../../testing/gate4-acceptance-verification.md)
is the evidence record for settings/security/runtime/static/operational/regression
acceptance and material-finding disposition.

- Final #83 HEAD CI [37062061257](https://github.com/SARD-81/dynamic-forms-platform/actions/runs/37062061257): all five required jobs SUCCESS, 487 tests.
- Final #95/#96 HEAD CI [37064542544](https://github.com/SARD-81/dynamic-forms-platform/actions/runs/37064542544): all five required jobs SUCCESS, 502 tests.
- Final acceptance correction #102 CI [37066499042](https://github.com/SARD-81/dynamic-forms-platform/actions/runs/37066499042): all five required jobs SUCCESS, 509 tests.
- Fresh exact technical SHA CI [37066868098](https://github.com/SARD-81/dynamic-forms-platform/actions/runs/37066868098): all five required jobs SUCCESS, 509 tests.
- Ruff format/lint, Django check/migration drift, existing development docker-smoke
  and actual production-smoke completed successfully.
- Production init/migrations/static/preflight, public login/home/API/OpenAPI/health/
  project/admin static, worker registration/Beat, internal-only dependencies,
  private-file denial, bounded DB/cache outages and proxy spoof resistance passed.
- No committed real secrets, generated junk, domain migration or overwritten
  frozen baseline was found. Material findings were fixed and reverified.

The closure/freeze PR requires all five checks successful on its own final HEAD,
clean synchronized current-dev scope and explicit Team Lead authorized Squash
merge. Its number/check/merge evidence and the final milestone evidence live in
#84/#77, rather than substituting a documentation SHA for technical acceptance.

## Release conditions and limitations

This accepts a reproducible repository production topology, not a running public
hosting environment. Operators supply TLS edge/certificates, real environment
secrets and SMTP/API destinations, backup/recovery procedures and deployment
values according to the environment/production contracts. CI deliberately uses
placeholder credentials, explicit local HTTP smoke and no real external delivery.
Secure cookies/default HTTPS redirect and the narrow trust contract are retained.

**#41 is deferred optional BONUS scope; HTTP reporting remains authoritative.**
#95/#96 final AmirReza code tasks are completed through PR #100. #41 is closed
not_planned after deferral, without falsely claiming WebSocket completion.
No BL-APPLICATION-002 is created because application semantics did not change.

## Promotion and closure contract

Gate 4 is CLOSED/FROZEN on dev when the authorized closure documentation merge
activates this acceptance. #84 and Tracker #77 remain open because their complete
DoD includes the final dev-to-main promotion. The milestone PR must have all five
required jobs completed SUCCESS and remain open for manual Team Lead review/merge.
This Work session grants no main merge authorization and never enables auto-merge.
After an explicitly authorized promotion, record the verified main commit and
close #84/#77; do not claim that step before it happens.
