# PostgreSQL Constraint Verification

**Gate:** 2E — Database Constraint Verification  
**Status:** COMPLETED / PASSED  
**Source baseline:** BL-DATA-002

## Purpose

Gate 2D proved that Django models and generated migrations represent the frozen schema.

Gate 2E proved that PostgreSQL actually enforces the frozen database rules.

SQLite was not used.

## Runtime evidence

Verified against PostgreSQL 16.15 with a dedicated local project role/database:

```text
python src/manage.py check
→ System check identified no issues

python src/manage.py migrate
→ complete initial migration graph applied successfully

python src/manage.py showmigrations accounts core forms processes reports
→ all project 0001_initial migrations applied

DJANGO_SETTINGS_MODULE=config.settings.test python src/manage.py test apps
→ Found 23 test(s)
→ Ran 23 tests
→ OK

python src/manage.py makemigrations --check --dry-run
→ No changes detected
```

Django successfully created and destroyed an isolated PostgreSQL test database.

## Test transaction pattern

Expected database violations assert `django.db.IntegrityError` inside an inner
`transaction.atomic()` block.

`TransactionManagementError` is not treated as a successful constraint assertion.

## Constraint coverage

The Gate 2E suite verifies frozen database rejection/uniqueness rules across:

- User / OTPChallenge
- Category
- Form / Question / QuestionOption
- Answer / AnswerOption
- Process / ProcessStep
- ProcessRun identity, token uniqueness, and state
- ProcessStepRun pair uniqueness, state consistency, and submission OneToOne ownership
- ReportSubscription delivery-target consistency

Cross-table Service-only invariants remain intentionally outside this database suite.

## Explicit verification boundaries

This gate does **not** claim behavioral verification of Django deletion policies such as
`PROTECT`, `SET_NULL`, or lifecycle-specific deletion rules. Those belong to the relevant
domain/service gates where deletion behavior and history preservation are exercised in context.

Indexes such as `report_active_freq_idx` are schema/query-performance artifacts, not rejection
constraints. Their usefulness is verified with real reporting/query workloads and query plans in
the reporting/query-optimization work.

## Test discovery

Because the repository uses a `src/` layout, Django's built-in runner required an explicit
`apps` label during Gate 2E:

```bash
DJANGO_SETTINGS_MODULE=config.settings.test python src/manage.py test apps
```

Gate 2F introduces pytest with `pythonpath = ["src"]` and explicit test paths, so ordinary
`pytest` becomes the standard test command.

## Local PostgreSQL contract

The development role:

- owns the local `dynamic_forms` database;
- is not a PostgreSQL superuser;
- has local `CREATEDB` permission so test runners can create an isolated database.

Database passwords stay in the ignored local `.env` file.
