# GATE 4 — Production Readiness, Release Hardening & Bonus Enhancements

**Status:** IN PROGRESS  
**Tracker:** GitHub Issue #77  
**Kickoff integration point:** `dev@53695eba20c39da8913bed27fdd16fd0efff6b4d`  
**Gate 3 promotion:** `main@419e71961ad68a7cca9b0ef04a13501ef6c4b8cd`

## Purpose

Gate 4 closes the production-delivery gap intentionally left outside the frozen Gate 3 scope while preserving frozen Gate 3 application/data semantics.

The mandatory goal is a reproducible production-oriented deployment with real ASGI serving, `collectstatic`, Nginx reverse-proxy/static serving, operational diagnostics and deterministic production verification.

Issue #41 real-time reporting remains optional and non-blocking.

## Authoritative inputs

Gate 4 consumes without rewriting:

- `BL-ARCH-002`;
- `BL-DATA-002`;
- `BL-FOUNDATION-002`;
- `BL-APPLICATION-001`;
- Gate 3 promoted state on `main`.

Structural production-runtime changes require explicit Change Control. Issue #78 owns CHG-0006.

## Team ownership

### Mahsa-Alipour

- #79 — production preflight management command and deployment-safety tests;
- #82 — reusable production HTTP/static smoke verifier.

Mahsa owns development tooling that directly supports #81, #83 and #84. Her work should stay mostly in new/self-contained files so it can proceed with minimal overlap with the production topology branch.

She does not own Nginx/Compose architecture, proxy/security decisions or Django Template/HTML work.

### amirrezaparvaneh

- #80 — operational health/readiness diagnostics and runtime logging;
- #83 — mandatory production topology CI smoke/regression.

AmirReza owns backend/operations/CI integration. #80 tests/scaffolding may begin in parallel, but runtime foundation changes must not merge before #78 authorizes the production-runtime boundary.

### SARD-81

- #78 — CHG-0006 production runtime authorization;
- #81 — production ASGI/Nginx/collectstatic topology;
- #84 — final integrated acceptance, baseline freeze and milestone promotion;
- #41 — optional real-time Channels/WebSockets work.

SARD-81 owns production architecture/security/change control, all Django Template/HTML/presentation-specific JavaScript work, final security/release verification, baselines and promotion.

## Parallel-work principle

The plan minimizes idle time and shared-file conflicts.

- #78, #79 and #80 test/scaffolding can begin immediately.
- #79 does not define production topology and therefore does not need to wait for #78.
- #81 starts after #78 is merged.
- after #79 stabilizes its command/interface, Mahsa moves directly to #82.
- #82 can implement its generic verifier without waiting for #81 internals; only final route/static assertions synchronize once #80/#81 interfaces are stable.
- #81 never waits for #82.
- #83 reuses #79/#82 tooling instead of duplicating the same checks in workflow YAML.

## WAVE 1 — Parallel kickoff

- #78 — SARD-81 — CHG-0006
- #79 — Mahsa — production preflight command/tests
- #80 — AmirReza — health/readiness/logging tests/scaffolding; runtime merge waits for #78

## WAVE 2 — Production implementation + verification tooling

- #81 — SARD-81 — production ASGI/Nginx/collectstatic; requires #78
- #82 — Mahsa — reusable production HTTP/static verifier; follows #79 and synchronizes final expectations with stable #80/#81 interfaces
- #80 — AmirReza — finalize runtime health/readiness/logging after #78 authorization

## WAVE 3 — Automated production verification

- #83 — AmirReza — mandatory `production-smoke` CI using #79/#82 tooling and stable #80/#81 runtime
- #41 — SARD-81 — optional real-time reporting after production proxy integration is stable

## WAVE 4 — Freeze / promotion

- #84 — SARD-81 — integrated production acceptance, security review, baseline freeze and milestone promotion

Mandatory dependency: #78–#83 complete. #41 is optional.

## Dependency map

```text
#78 CHG-0006 [SARD-81] ───────→ #81 Production runtime [SARD-81] ───────┐
       │                                                                  │
       └────────→ #80 runtime application [AmirReza] ─────────────────────┤
                                                                            ↓
#79 Production preflight [Mahsa] ─→ #82 HTTP/static verifier [Mahsa] ─→ #83 production-smoke [AmirReza]
                                                                            │
#81 ──→ optional #41 Real-time [SARD-81]                                    │
                                                                            ↓
                         #78 + #79 + #80 + #81 + #82 + #83
                                            ↓
                                   #84 Gate 4 closure
                                   [SARD-81]
```

## Mandatory production contract target

Gate 4 must verify all of the following before closure:

1. production settings load through `config.settings.production`;
2. production application serving does not use Django `runserver`;
3. the ASGI application is served directly through the approved command;
4. Nginx is the public reverse-proxy/static boundary;
5. `collectstatic --noinput` produces production static assets;
6. Nginx serves collected static files;
7. PostgreSQL remains the source of truth;
8. Redis retains the required cache/Celery role separation;
9. Celery worker/Beat scheduled delivery remains operational;
10. secrets remain environment/settings owned;
11. proxy/HTTPS/security handling is explicit and regression-tested;
12. liveness/readiness and production-safe logging exist;
13. #79 application preflight is reusable from production/local CI;
14. #82 external verifier validates public HTTP/static behavior;
15. #83 provides deterministic automated production-topology verification;
16. Gate 3 application semantics remain regression-green.

## Required CI

Existing jobs remain required:

- `lint`;
- `test`;
- `migration-check`;
- `docker-smoke`.

#83 must add a stable `production-smoke` job, or an explicitly equivalent required job named by #83/#84. Gate 4 cannot close without green automated production-topology verification.

## Change-control / baseline plan

### CHG-0006

Owned by #78. It authorizes production runtime/topology and the integration boundaries consumed by #80/#81/#83 before those runtime changes are merged.

### Proposed Gate 4 baselines

At closure, if verified implementation warrants them:

- `BL-FOUNDATION-003` — production-ready active foundation;
- `BL-RELEASE-001` — Gate 4 production/release acceptance baseline.

`BL-APPLICATION-001` remains authoritative unless application semantics actually change through explicit control.

## Bonus #41

Real-time reporting remains optional.

If implemented, it must use the previously authorized Channels/Redis boundary, authorize WebSocket subscriptions by ownership, emit only after transaction commit, preserve HTTP reporting as correctness fallback and integrate WebSocket ingress through #81 Nginx.

## Governance

`CHG-0005` was a Gate 3 governance record and is not silently extended to Gate 4.

Until a Gate 4-specific governance record explicitly changes the rule, Gate 4 PRs use the repository's normal independent peer-review requirement in addition to required green CI and Team Lead verification/merge decision.

Material automated/manual findings must be resolved or explicitly accepted with evidence.

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
- [ ] #79 preflight verified
- [ ] #82 HTTP/static verifier verified
- [ ] PostgreSQL/Redis/Celery runtime verified
- [ ] full pytest green
- [ ] migration drift green
- [ ] development `docker-smoke` green
- [ ] `production-smoke` green
- [ ] documentation synchronized
- [ ] #41 completed or explicitly deferred
- [ ] `BL-FOUNDATION-003` frozen if required by applied topology
- [ ] `BL-RELEASE-001` frozen
- [ ] #84 integrated acceptance complete
- [ ] Gate 4 CLOSED / FROZEN
- [ ] separate `dev → main` milestone CI + active Gate 4 review/merge governance complete
- [ ] milestone explicitly merged
- [ ] tracker #77 closed
