# PostgreSQL Constraint Verification

**Gate:** 2E — Database Constraint Verification  
**Status:** IN PROGRESS  
**Source baseline:** BL-DATA-002

## Purpose

Gate 2D proved that Django models and generated migrations represent the frozen schema.

Gate 2E proves that PostgreSQL actually enforces the frozen database rules.

SQLite is not permitted for this verification.

## Test runner boundary

Gate 2F owns the formal pytest/Ruff foundation.

Gate 2E therefore uses Django's built-in test runner and `django.test.TestCase`. These tests remain compatible with later pytest-django adoption.

Expected database violations assert `django.db.IntegrityError` inside an inner `transaction.atomic()` block.

`TransactionManagementError` is not the expected constraint result; it normally indicates code continued using a transaction after a database error without an appropriate rollback boundary.

## First PostgreSQL application sequence

After a dedicated local PostgreSQL database and role are configured:

```bash
python src/manage.py migrate
python src/manage.py showmigrations
env DJANGO_SETTINGS_MODULE=config.settings.test python src/manage.py test apps
python src/manage.py makemigrations --check --dry-run
```

The first `migrate` is allowed only because the complete initial migration graph was merged in Gate 2D.

## Constraint coverage

The Gate 2E suite covers critical and custom frozen DB constraints across:

- User / OTPChallenge
- Category
- Form / Question / QuestionOption
- Answer / AnswerOption
- Process / ProcessStep
- ProcessRun identity, token uniqueness, and state
- ProcessStepRun identity/state/OneToOne ownership
- ReportSubscription delivery target consistency

Cross-table Service-only invariants remain intentionally outside this database suite.

## Local PostgreSQL values

Use a dedicated local development role/database. Do not use a superuser account from Django.

Suggested local values:

```text
POSTGRES_DB=dynamic_forms
POSTGRES_USER=dynamic_forms
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

The password is local-only and belongs in `.env`, never in Git.


## Test discovery note

Because the repository uses a `src/` layout, running:

```bash
python src/manage.py test
```

from the repository root may report `Found 0 test(s)` because default unittest discovery starts from the current working directory and does not automatically treat `src/` as a package discovery root.

Use the explicit project package label instead:

```bash
DJANGO_SETTINGS_MODULE=config.settings.test python src/manage.py test apps
```

This is a discovery-path correction only; it does not indicate that migrations or database constraints failed.
