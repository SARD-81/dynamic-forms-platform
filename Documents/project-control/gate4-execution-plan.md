# GATE 4 — Production Readiness, Release Hardening & Bonus Enhancements

**Status:** IN PROGRESS  
**Tracker:** GitHub Issue #77  
**Current integration branch:** `dev`  
**Gate 3 promotion:** `main@419e71961ad68a7cca9b0ef04a13501ef6c4b8cd`

## Purpose

Gate 4 closes the production-delivery gap intentionally left outside the frozen Gate 3 scope while preserving frozen Gate 3 application/data semantics.

The original project brief requires a production-mode path with production settings, a real production web server, production static collection and Docker/environment-based deployment configuration. Nginx is not itself a mandatory brief requirement; Gate 4 deliberately selects Nginx as the production reverse-proxy/static-serving topology because it gives the project one explicit public ingress boundary and a clean later WebSocket integration point.

Issue #41 real-time reporting remains optional and non-blocking.

## Authoritative inputs

Gate 4 consumes without rewriting:

- `BL-ARCH-002`;
- `BL-DATA-002`;
- `BL-FOUNDATION-002`;
- `BL-APPLICATION-001`;
- Gate 3 promoted state on `main`.

Structural production-runtime changes require explicit Change Control. Issue #78 owns CHG-0006.

Gate 4 merge governance is defined separately from CHG-0006 and must not be inferred from Gate 3-only CHG-0005.

## Current repository state at control-plane repair

- Gate 3 is CLOSED / FROZEN / PROMOTED;
- #79 production preflight implementation was merged through PR #88 and is available on `dev`;
- #80 has an implementation PR (#87) but its runtime/foundation changes remain blocked from merge until #78 / CHG-0006 is approved and merged;
- the original Gate 4 kickoff PR #85 was created from the pre-#79 integration state and is superseded by the current control-plane synchronization;
- draft PR #86 is stale against the current integration state and must be refreshed/re-scoped or superseded rather than merged as-is.

## Team ownership

### Mahsa-Alipour

- #79 — production preflight management command and deployment-safety tests — **IMPLEMENTED / MERGED via PR #88; issue bookkeeping pending control-plane sync**;
- #82 — reusable production HTTP/static smoke verifier.

Mahsa owns development tooling that directly supports #81, #83 and #84. Her work should stay mostly in new/self-contained files so it can proceed with minimal overlap with the production topology branch.

She does not own Nginx/Compose architecture, proxy/security decisions or Django Template/HTML work.

### amirrezaparvaneh

- #80 — operational health/readiness diagnostics and runtime logging;
- #83 — mandatory production topology CI smoke/regression.

AmirReza owns backend/operations/CI integration. #80 tests/scaffolding may proceed, but runtime/foundation changes must not merge before #78 authorizes the production-runtime boundary. PR #87 must be synchronized with current `dev` after that authorization before final review.

### SARD-81

- #78 — CHG-0006 production runtime authorization;
- #81 — production ASGI/Nginx/collectstatic topology;
- #84 — final integrated acceptance, baseline freeze and milestone promotion;
- #41 — optional real-time Channels/WebSockets work.

SARD-81 owns production architecture/security/change control, all Django Template/HTML/presentation-specific JavaScript work, final security/release verification, baselines and promotion.

## Parallel-work principle

The plan minimizes idle time and shared-file conflicts.

- #79 is already merged and provides the stable `production_preflight` command contract consumed downstream.
- #78 is now the mandatory control-plane blocker for production runtime changes.
- #80 implementation may remain open but cannot merge until #78 is effective.
- #81 starts only after #78 is merged.
- Mahsa may proceed to #82 using the stable #79 command and generic HTTP-verifier design; final route/static assertions synchronize against #80/#81.
- #81 never waits for #82.
- #83 reuses #79/#82 tooling instead of duplicating the same checks in workflow YAML.

## WAVE 1 — Control and parallel tooling

- #78 — SARD-81 — CHG-0006 production runtime authorization — **NEXT MANDATORY OWNER TASK**
- #79 — Mahsa — production preflight command/tests — **MERGED**
- #80 — AmirReza — health/readiness/logging implementation — **PR #87 OPEN; MERGE BLOCKED BY #78**

## WAVE 2 — Production implementation + verification tooling

- #81 — SARD-81 — production ASGI/Nginx/collectstatic; requires merged #78
- #82 — Mahsa — reusable production HTTP/static verifier; follows #79 and synchronizes final expectations with stable #80/#81 interfaces
- #80 — AmirReza — synchronize/finalize runtime health/readiness/logging after #78 authorization

## WAVE 3 — Automated production verification

- #83 — AmirReza — mandatory `production-smoke` CI using #79/#82 tooling and stable #80/#81 runtime
- #41 — SARD-81 — optional real-time reporting after production proxy integration is stable

## WAVE 4 — Freeze / promotion

- #84 — SARD-81 — integrated production acceptance, security review, baseline freeze and milestone promotion

Mandatory dependency: #78–#83 complete. #41 is optional.

## Dependency map

```text
#79 Production preflight [Mahsa] — MERGED ───────────────────────────────┐
                                                                        │
#78 CHG-0006 [SARD-81] ───────→ #81 Production runtime [SARD-81] ──────┤
       │                                                                 │
       └────────→ #80 runtime merge [AmirReza] ──────────────────────────┤
                                                                        ↓
#82 HTTP/static verifier [Mahsa] ───────────────────────────────→ #83 production-smoke [AmirReza]
                                                                        │
#81 ──→ optional #41 Real-time [SARD-81]                                 │
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
3. the ASGI application is served directly through the approved production command;
4. Nginx is the selected public reverse-proxy/static boundary for this repository's production topology;
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

### Gate 4 governance change

Gate 3 CHG-0005 is not silently extended. Gate 4 adopts its own explicit Team Lead Verification record so independent peer `APPROVED` review is optional rather than an automatic merge prerequisite. The transition record must preserve the historical classification of work merged before it became effective.

### Proposed Gate 4 baselines

At closure, if verified implementation warrants them:

- `BL-FOUNDATION-003` — production-ready active foundation;
- `BL-RELEASE-001` — Gate 4 production/release acceptance baseline.

`BL-APPLICATION-001` remains authoritative unless application semantics actually change through explicit control.

## Bonus #41

Real-time reporting remains optional.

If implemented, it must use the previously authorized Channels/Redis boundary, authorize WebSocket subscriptions by ownership, emit only after transaction commit, preserve HTTP reporting as correctness fallback and integrate WebSocket ingress through #81 Nginx.

## Governance

Gate 4 does not inherit CHG-0005 merely by implication. Its explicit governance transition establishes Team Lead Verification for Gate 4 using the same technical controls:

```text
Issue
→ short-lived branch from current dev
→ implementation/tests
→ Pull Request to dev
→ required CI green
→ material findings resolved or explicitly accepted with evidence
→ Team Lead Verification
→ explicit Team Lead merge decision
```

Independent peer review remains welcome but optional. Reviewer requests are not required merely to satisfy process.

No assistant-initiated merge is authorized: PRs remain open for the repository owner/Team Lead to review and merge explicitly.

## Gate 4 exit criteria

- [ ] #78 complete
- [x] #79 implementation merged via PR #88; issue/tracker closeout synchronized
- [ ] #80 complete
- [ ] #81 complete
- [ ] #82 complete
- [ ] #83 complete
- [ ] clean production-oriented bootstrap verified
- [ ] `collectstatic` + Nginx static serving verified
- [ ] production ASGI serving verified without `runserver`
- [ ] proxy/security/environment boundaries verified
- [ ] health/readiness/logging verified
- [ ] #79 preflight verified in production topology
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
- [ ] milestone explicitly merged by Team Lead
- [ ] tracker #77 closed
