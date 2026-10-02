# GATE 4 — Production Readiness, Release Hardening & Bonus Enhancements

**Status:** IN PROGRESS  
**Tracker:** GitHub Issue #77  
**Current integration state at control-plane repair:** `dev@4b232c41cbbc45b58dbb468b63bcdcfbde0ea76a`  
**Gate 3 promotion:** `main@419e71961ad68a7cca9b0ef04a13501ef6c4b8cd`

## Purpose

Gate 4 closes the production-delivery gap intentionally left outside the frozen Gate 3 scope while preserving frozen Gate 3 application/data semantics.

The project brief requires a production-mode deployment path, production-oriented web serving, production settings/static collection, Dockerization and environment-owned configuration. Reverse proxy usage such as Nginx is listed by the brief as bonus/extra-credit scope rather than a mandatory named technology.

For this project, Gate 4 deliberately selects Nginx as the production reverse-proxy/static-serving boundary because it gives the release topology one clear public ingress and supports later optional WebSocket proxying. This is a team topology decision, not a claim that the brief itself mandates Nginx.

Issue #41 real-time reporting remains optional and non-blocking.

## Authoritative inputs

Gate 4 consumes without rewriting:

- `BL-ARCH-002`;
- `BL-DATA-002`;
- `BL-FOUNDATION-002`;
- `BL-APPLICATION-001`;
- Gate 3 promoted state on `main`.

Structural production-runtime changes require explicit Change Control. Issue #78 owns CHG-0006. Gate 4 merge governance is owned by Issue #89 / CHG-0007.

## Current Wave 1 state

- #79 — **COMPLETED** through PR #88; production preflight interface is now available on `dev`;
- #80 — implementation exists in Draft PR #87 but runtime/settings changes are **BLOCKED FROM MERGE** until #78 / CHG-0006 is approved/applied and the branch is synchronized with current `dev`;
- #78 — current primary Team Lead task; authorizes the production runtime/topology boundary;
- #82 — may begin from the stable #79 interface and finalize against stable #80/#81 public contracts;
- #85 — superseded stale kickoff PR;
- #86 — superseded stale #79 documentation draft;
- #89 / CHG-0007 — Gate 4 governance transition; becomes effective only when its transition PR is merged.

## Team ownership

### Mahsa-Alipour

- [x] #79 — production preflight management command and deployment-safety tests;
- [ ] #82 — reusable production HTTP/static smoke verifier.

Mahsa owns development tooling that directly supports #81, #83 and #84. Her work should remain mostly in new/self-contained files to minimize overlap with production topology work.

She does not own Nginx/Compose architecture, proxy/security decisions or Django Template/HTML work.

### amirrezaparvaneh

- [ ] #80 — operational health/readiness diagnostics and runtime logging;
- [ ] #83 — mandatory production topology CI smoke/regression.

AmirReza owns backend/operations/CI integration. #80 implementation may exist in parallel, but runtime foundation changes must not merge before #78 authorizes the production-runtime boundary.

### SARD-81

- [ ] #78 — CHG-0006 production runtime authorization;
- [ ] #81 — production ASGI/Nginx/collectstatic topology;
- [ ] #84 — final integrated acceptance, baseline freeze and milestone promotion;
- [ ] #41 — optional real-time Channels/WebSockets work;
- [ ] #89 — CHG-0007 Gate 4 governance transition.

SARD-81 owns production architecture/security/change control, all Django Template/HTML/presentation-specific JavaScript work, final security/release verification, baselines and promotion.

## Parallel-work principle

- #78 is the mandatory authorization blocker for #81 and the runtime portion of #80.
- #79 is complete and its stable command interface may be consumed immediately.
- #82 can proceed using #79 and remain independent from Nginx/Compose internals; final route/static assertions synchronize with stable #80/#81 interfaces.
- #81 starts only after #78 is merged.
- #80 returns from Draft only after #78 is merged and its branch is synchronized with current `dev`.
- #83 reuses #79/#82 tooling instead of duplicating those checks in workflow YAML.
- #41 is optional and should wait until production proxy topology is stable if selected.

## WAVE 1 — Authorization + operational interfaces

- #89 — SARD-81 — Gate 4 governance transition / CHG-0007
- #78 — SARD-81 — production runtime authorization / CHG-0006
- #79 — Mahsa — **DONE** production preflight command/tests
- #80 — AmirReza — Draft implementation held pending #78

## WAVE 2 — Production implementation + verification tooling

- #81 — SARD-81 — production ASGI/Nginx/collectstatic; requires #78
- #82 — Mahsa — reusable production HTTP/static verifier
- #80 — AmirReza — synchronize/finalize runtime health/readiness/logging after #78 authorization

## WAVE 3 — Automated production verification

- #83 — AmirReza — mandatory `production-smoke` CI using #79/#82 tooling and stable #80/#81 runtime
- #41 — SARD-81 — optional real-time reporting after production proxy integration is stable

## WAVE 4 — Freeze / promotion

- #84 — SARD-81 — integrated production acceptance, security review, baseline freeze and milestone promotion

Mandatory dependency for Gate 4 closure: #78–#83 complete. #41 is optional.

## Dependency map

```text
#89 CHG-0007 governance [SARD-81] ──→ active Gate 4 merge workflow

#78 CHG-0006 [SARD-81] ───────→ #81 Production runtime [SARD-81] ───────┐
       │                                                                  │
       └────────→ #80 runtime application [AmirReza] ─────────────────────┤
                                                                            ↓
#79 Preflight [Mahsa] DONE ─→ #82 HTTP/static verifier [Mahsa] ─────→ #83 production-smoke [AmirReza]
                                                                            │
#81 ──→ optional #41 Real-time [SARD-81]                                    │
                                                                            ↓
                         #78 + #79 + #80 + #81 + #82 + #83
                                            ↓
                                   #84 Gate 4 closure
```

## Mandatory production contract target

Before Gate 4 closes, verify:

1. production settings load through `config.settings.production`;
2. production serving does not use Django `runserver`;
3. the Django ASGI application is served by the approved production command (reuse Daphne unless CHG-0006 separately justifies another dependency);
4. Nginx is the selected public reverse-proxy/static boundary;
5. `collectstatic --noinput` produces production static assets;
6. Nginx serves collected static files;
7. no source-code bind mount exists in the production-oriented topology;
8. PostgreSQL/Redis/Celery internals are not exposed as public ingress;
9. Celery worker/Beat scheduled delivery remains operational;
10. secrets remain environment/settings owned;
11. proxy/HTTPS/security handling is explicit and regression-tested;
12. liveness/readiness and production-safe logging exist;
13. #79 `production_preflight` is reused rather than reimplemented;
14. #82 external verifier validates public HTTP/static behavior;
15. #83 provides deterministic automated production-topology verification;
16. Gate 3 application semantics remain regression-green.

## Required CI

Current required jobs remain:

- `lint`;
- `test`;
- `migration-check`;
- `docker-smoke`.

#83 must add stable `production-smoke` verification. Once introduced, it is mandatory for Gate 4 closure and `dev → main` promotion.

## Change-control / baseline plan

### CHG-0006 — production runtime

Owned by #78. It authorizes the exact topology/runtime/security boundary before #81 and the runtime portion of #80 may merge.

### CHG-0007 — Gate 4 governance

Owned by #89. It adopts Team Lead Verification for Gate 4 without silently extending Gate 3 CHG-0005. Independent peer approval becomes optional after CHG-0007 is merged; Team Lead review/explicit merge authorization remains mandatory.

### Gate 4 baselines

At closure, after implementation is actually applied and verified:

- `BL-FOUNDATION-003` — active production-ready engineering/runtime foundation;
- `BL-RELEASE-001` — Gate 4 production/release acceptance baseline.

`BL-APPLICATION-001` remains authoritative unless Gate 4 deliberately changes frozen application semantics through explicit change control.

## Bonus #41

Real-time reporting remains optional. If implemented, it must preserve HTTP reporting as correctness fallback, authorize subscriptions by resource ownership, emit only after committed changes and integrate WebSocket ingress through the stable #81 public proxy topology.

## Gate 4 governance

After CHG-0007 becomes effective:

```text
Issue → branch from current dev → implementation/tests → PR → required CI green → Team Lead Verification → explicit Team Lead merge decision
```

Independent peer approval is optional and no reviewer is auto-requested solely to satisfy process. Material automated/manual findings remain mandatory verification inputs and must be resolved or explicitly accepted with evidence.

The CHG-0007 transition PR itself is a one-time Team Lead-authorized governance transition and does not make the new rule retroactive.

## Exit criteria

- [ ] #89 / CHG-0007 effective
- [ ] #78 / CHG-0006 complete
- [x] #79 complete
- [ ] #80 complete
- [ ] #81 complete
- [ ] #82 complete
- [ ] #83 complete
- [ ] clean production-oriented bootstrap verified
- [ ] production ASGI serving verified without `runserver`
- [ ] `collectstatic` + Nginx static serving verified
- [ ] proxy/security/environment boundaries verified
- [ ] health/readiness/logging verified
- [ ] #79 preflight reused and verified
- [ ] #82 external HTTP/static verifier verified
- [ ] PostgreSQL/Redis/Celery runtime verified
- [ ] full pytest green
- [ ] migration drift green
- [ ] development `docker-smoke` green
- [ ] `production-smoke` green
- [ ] documentation synchronized
- [ ] #41 completed or explicitly deferred
- [ ] `BL-FOUNDATION-003` frozen
- [ ] `BL-RELEASE-001` frozen
- [ ] #84 integrated acceptance complete
- [ ] Gate 4 CLOSED / FROZEN
- [ ] separate `dev → main` milestone CI + Team Lead Verification complete
- [ ] milestone explicitly merged by Team Lead
- [ ] tracker #77 closed
