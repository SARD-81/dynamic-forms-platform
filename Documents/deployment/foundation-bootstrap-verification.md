# Foundation Bootstrap Verification

**Gate:** 2I — Developer Workflow, README & Foundation Verification  
**Status:** VERIFIED WITH FOLLOW-UP HYGIENE FIX  
**Target baseline:** BL-FOUNDATION-001

## Purpose

Prove that the Gate 2 foundation is usable by a developer starting from a fresh repository clone,
without relying on undocumented local state.

## Clean-start assumptions

The verification directory began with:

- a fresh clone;
- no project `.env`;
- no project virtual environment;
- no existing Docker Compose project/volume for that clone.

Docker Engine and Docker Compose v2 were already installed.

## Verification run — 2026-09-21

Environment:

- OS: Ubuntu 24.04
- Docker: 29.1.3
- Docker Compose: 2.40.3
- source branch used before merge: `docs/17-developer-workflow-verification`
- clean clone directory: `dynamic-forms-platform-cleancheck`

Observed path:

1. cloned the repository;
2. checked out the Gate 2I branch;
3. copied `.env.example` to `.env`;
4. generated fresh local-only Django/database secrets;
5. `docker compose --env-file .env config --quiet` passed;
6. `docker compose up --build -d` succeeded;
7. PostgreSQL became healthy;
8. Redis became healthy;
9. web started on port 8000;
10. Django system check passed;
11. pytest reported `config.settings.test`;
12. 24/24 tests passed;
13. `HEAD /admin/login/` returned HTTP 200;
14. response server reported Daphne;
15. `git status --short` was empty.

Observed wall-clock bootstrap from clone start to completed verification was approximately three
minutes on the verification machine. Docker layer/image cache was available; the Gate 2 target
explicitly excludes image-download/network time.

## Discovered cleanup hygiene issue

The first clean verification exposed one onboarding hygiene issue after all functional checks had
already passed.

Because the development web container runs as root and the repository is bind-mounted, pytest's
default cache provider created `.pytest_cache` on the host with root ownership. The ignored cache
did not dirty Git, but it prevented an ordinary host user from deleting the temporary clone.

This did not affect application/runtime correctness, but it is a valid developer-experience defect.

## Applied fix

The Docker `web` service now sets:

```text
PYTEST_ADDOPTS=-p no:cacheprovider
```

This disables only pytest's cache provider inside the Docker development service, preventing
container-root cache files from being written into the host bind mount.

Host/non-Docker pytest keeps its normal cache behavior.

## Final hygiene verification required

After the fix, one focused check remains:

1. run Docker pytest from a clean checkout;
2. confirm `.pytest_cache` is not created by the container;
3. stop/remove the Compose stack and volume;
4. remove the clean-check directory as the normal host user, without `sudo`.

No repetition of the already-passed functional acceptance checks is required beyond confirming the
test suite still passes.

## Independent developer status

Collaborator repository access was still inactive during Gate 2I, so an independent teammate
verification could not be assigned through GitHub.

An owner-run fresh-clone verification is accepted for Gate 2I. A teammate may repeat this checklist
later as an onboarding exercise without changing BL-FOUNDATION-001.

## Gate exit

Gate 2I closes when:

- CI is green on the cleanup-hygiene fix;
- Docker pytest still passes;
- no container-created `.pytest_cache` appears on the host;
- the temporary clean clone can be deleted without elevated privileges.
