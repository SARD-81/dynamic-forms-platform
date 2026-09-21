# Foundation Bootstrap Verification

**Gate:** 2I — Developer Workflow, README & Foundation Verification  
**Status:** IN PROGRESS  
**Target baseline:** BL-FOUNDATION-001

## Purpose

Prove that the Gate 2 foundation is usable by a developer starting from a fresh repository clone,
without relying on undocumented local state.

## Clean-start assumptions

The verification directory must begin with:

- a fresh clone;
- no project `.env`;
- no project virtual environment;
- no existing Docker Compose project/volume for this clone.

Docker Engine/Desktop and Docker Compose v2 may already be installed.

## Required path

1. clone the repository;
2. switch to `dev`;
3. copy `.env.example` to `.env`;
4. replace `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD`;
5. run `docker compose --env-file .env config --quiet`;
6. run `docker compose up --build -d`;
7. verify `postgres` and `redis` are healthy;
8. verify `web` is running;
9. open or request `http://localhost:8000/admin/login/`;
10. run `docker compose exec web python src/manage.py check`;
11. run `docker compose exec web pytest`;
12. confirm pytest reports `config.settings.test`;
13. run `git status --short` and confirm the clone has no tracked modifications.

## Time objective

Target: under 15 minutes from completed clone to green application/test verification, excluding
network/image-download time.

## Evidence to record

Record:

- OS
- Docker version
- Docker Compose version
- elapsed bootstrap time
- `docker compose ps`
- Django system-check result
- pytest result and settings module
- HTTP result
- `git status --short`

## Independent developer status

At the start of Gate 2I, collaborator repository access is still not active, so an independent
teammate verification cannot yet be assigned through GitHub.

An owner-run fresh-clone verification is accepted for Gate 2I. A teammate may repeat the same
checklist later as an onboarding exercise without changing BL-FOUNDATION-001.

## Gate exit

Gate 2I closes only after:

- README Quick Start matches this checklist;
- CI is green;
- fresh-clone verification evidence is recorded;
- no known foundation documentation contradicts actual runtime behavior.
