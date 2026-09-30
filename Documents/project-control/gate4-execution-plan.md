# GATE 4 — Production Readiness, Release Hardening & Bonus Enhancements

**Status:** IN PROGRESS  
**Tracker:** GitHub Issue #77  
**Kickoff integration point:** `dev@53695eba20c39da8913bed27fdd16fd0efff6b4d`  
**Gate 3 promotion:** `main@419e71961ad68a7cca9b0ef04a13501ef6c4b8cd`

## Purpose

Gate 4 closes the production-delivery gap intentionally left outside the frozen Gate 3 scope.

The mandatory goal is a reproducible production-oriented deployment contract using the existing Django/ASGI application while preserving the frozen Gate 3 application and data semantics.

The original project requirements include production mode, a real web-server execution path and production static-file handling through `collectstatic`. Gate 3 completed and froze the application feature set but explicitly left production deployment/Nginx outside its scope. Gate 4 owns that boundary.

Nginx is used as the production reverse-proxy/static-serving boundary. Real-time reporting through Channels/WebSockets remains optional BONUS/STRETCH scope.

## Authoritative inputs

Gate 4 consumes without rewriting:

- `BL-ARCH-002` — architecture authority;
- `BL-DATA-002` — data/domain authority;
- `BL-FOUNDATION-002` — frozen active Gate 3 engineering/runtime foundation;
- `BL-APPLICATION-001` — frozen mandatory Gate 3 application behavior;
- `CHG-0005` — Team Lead Verification governance.

Any structural production-runtime change must use Change Control. Issue #78 owns `CHG-0006` before the production topology is implemented.

## Difficulty-based ownership

### Mahsa-Alipour — LIGHT

- #79 — production requirements traceability and release-evidence matrix;
- #82 — production deployment runbook and manual release acceptance.

Mahsa owns documentation QA, traceability and manual evidence. She does not own production architecture, Docker/Nginx implementation, security-critical configuration, or Django Template implementation.

### amirrezaparvaneh — MEDIUM

- #80 — operational health/readiness diagnostics and runtime logging contract;
- #83 — production topology CI smoke and operational regression.

AmirReza owns bounded backend/operations/CI work that consumes the Team Lead-defined production architecture.

### SARD-81 — HARD / CRITICAL

- #78 — CHG-0006 production runtime authorization;
- #81 — production ASGI/Nginx/collectstatic topology;
- #84 — final production acceptance, baseline freeze and milestone promotion;
- #41 — optional real-time reporting / Channels-WebSockets.

SARD-81 also remains the exclusive owner of Django Template/HTML/presentation-specific JavaScript work.

## Non-pending scheduling principle

Every member has an independent Wave 1 task.

The plan avoids assigning downstream work before its prerequisite exists, but allows safe documentation/test scaffolding to begin early. If a member is temporarily blocked, they continue pre-approved verification/documentation preparation inside their assigned Issue instead of inventing unrelated architecture.

## WAVE 1 — Parallel kickoff

Start immediately:

- #78 — SARD-81 — CHG-0006 production topology authorization;
- #79 — Mahsa — requirements/evidence matrix;
- #80 — AmirReza — health/readiness/logging.

No Wave 1 Issue depends on another Gate 4 implementation branch.

## WAVE 2 — Production runtime

- #81 — SARD-81 — production ASGI + Nginx + collectstatic; requires #78;
- #82 — Mahsa — runbook skeleton may start after #78 and final evidence is completed after #81.

AmirReza continues/finalizes #80 while #81 is under implementation.

## WAVE 3 — Production verification

- #83 — AmirReza — production-smoke CI; requires stable #80 and #81 interfaces;
- #82 — Mahsa — final manual release acceptance against the implemented runtime;
- #41 — SARD-81 — optional bonus real-time reporting may proceed after #81 if selected for this Gate.

If #41 is deferred, it does not block Wave 4.

## WAVE 4 — Freeze / promotion

- #84 — SARD-81 — integrated production acceptance, security review, baseline freeze and milestone promotion.

Mandatory dependency: #78–#83 complete. #41 is optional.

## Dependency map

```text
WAVE 1 (parallel)

#78 CHG-0006 [SARD-81 / HARD] ───────────────┐
                                               ↓
                                      #81 Production runtime
                                      [SARD-81 / HARD]
                                               │
                                               ├──────────────┐
                                               ↓              ↓
#79 Requirements matrix                 #82 Runbook       #83 Production CI
[Mahsa / LIGHT] ───────────────────────→ [Mahsa / LIGHT]  [AmirReza / MEDIUM]
                                                              ↑
#80 Health/readiness/logging ─────────────────────────────────┘
[AmirReza / MEDIUM]

#81 ──→ optional #41 Real-time [SARD-81 / BONUS HARD]

#78 + #79 + #80 + #81 + #82 + #83
                    ↓
              #84 Gate 4 closure
              [SARD-81 / HARD]
```

## Mandatory production contract target

Gate 4 must verify all of the following before closure:

1. production settings load through `config.settings.production`;
2. production application serving does not use Django `runserver`;
3. the ASGI application is served directly through the approved web-server command;
4. Nginx is the public reverse-proxy/static boundary;
5. `collectstatic --noinput` produces the production static artifact set;
6. Nginx serves collected static files;
7. PostgreSQL remains the source of truth;
8. Redis remains the required cache/Celery runtime with existing logical-role separation;
9. Celery worker/Beat scheduled delivery remains operational;
10. secrets remain environment/settings owned;
11. proxy/HTTPS/security handling is explicit and regression-tested;
12. liveness/readiness and production-safe logging exist;
13. production startup is reproducible from a clean checkout/environment;
14. Gate 3 application semantics remain regression-green.

## CI / verification target

Gate 3 stable jobs remain required:

- `lint`;
- `test`;
- `migration-check`;
- `docker-smoke`.

Issue #83 may add a stable `production-smoke` job after CHG-0006 authorizes the production-runtime quality boundary. Gate 4 closure must record the final required-check set explicitly.

## Change-control / baseline plan

### CHG-0006

Owned by #78. It authorizes the production runtime/topology before implementation.

### Proposed Gate 4 baselines

At closure, if verified implementation warrants them:

- `BL-FOUNDATION-003` — active production-ready foundation, superseding BL-FOUNDATION-002 only for active foundation state;
- `BL-RELEASE-001` — Gate 4 production/release acceptance baseline.

`BL-APPLICATION-001` remains authoritative unless Gate 4 intentionally changes application semantics. Production packaging alone does not justify `BL-APPLICATION-002`.

## Bonus #41

Issue #41 real-time reporting remains optional.

If implemented:

- use Redis DB 2 for Channels;
- use only the `channels-redis` boundary already authorized by CHG-0003 unless superseded by a new Change Record;
- authorize WebSocket connections by resource ownership;
- emit events only after transaction commit;
- keep HTTP reporting authoritative;
- integrate WebSocket upgrades through the production Nginx ingress from #81.

If deferred, Gate 4 records that decision and still remains eligible to close.

## Explicitly out of scope

Without a separately approved Issue/Change Record, Gate 4 does not include:

- Kubernetes;
- cloud-provider-specific infrastructure/IaC;
- multi-node HA;
- GraphQL;
- Google/social login;
- provider-specific certificate automation;
- unrelated schema/domain redesign.

## Governance / Definition of Done

CHG-0005 remains active:

```text
Issue
→ short-lived branch from current dev
→ implementation/tests
→ Pull Request
→ required CI green
→ Team Lead Verification
→ explicit Team Lead merge decision
```

For every mandatory Issue:

- scope remains inside its Issue;
- frozen architecture/data/application semantics are preserved or changed only through explicit control;
- material review findings are resolved or explicitly accepted with evidence;
- no unintended migration/model drift;
- applicable security tests exist;
- documentation is synchronized;
- required CI is green.

## Gate 4 exit criteria

- [ ] #78 complete
- [ ] #79 complete
- [ ] #80 complete
- [ ] #81 complete
- [ ] #82 complete
- [ ] #83 complete
- [ ] clean production-oriented bootstrap verified
- [ ] `collectstatic` + Nginx static serving verified
- [ ] production ASGI serving verified without `runserver`
- [ ] proxy/security/environment boundaries verified
- [ ] health/readiness/logging verified
- [ ] PostgreSQL/Redis/Celery runtime verified
- [ ] full pytest green
- [ ] migration drift green
- [ ] development docker-smoke green
- [ ] production-smoke green
- [ ] release/runbook evidence complete
- [ ] #41 completed or explicitly deferred
- [ ] `BL-FOUNDATION-003` frozen if required by applied topology
- [ ] `BL-RELEASE-001` frozen
- [ ] #84 integrated acceptance complete
- [ ] Gate 4 CLOSED / FROZEN
- [ ] separate `dev → main` milestone CI + Team Lead Verification complete
- [ ] milestone explicitly merged
- [ ] Tracker #77 closed
