# Quality and Test Foundation

**Gate:** 2F — Quality & Test Foundation  
**Status:** IN PROGRESS  
**Target baseline:** BL-FOUNDATION-001

## Standard commands

Install runtime + development dependencies:

```bash
python -m pip install -r requirements/dev.txt
```

Run lint:

```bash
ruff check .
```

Check formatting:

```bash
ruff format --check .
```

Run tests:

```bash
pytest
```

Run coverage:

```bash
coverage run -m pytest
coverage report -m
```

Verify no model/migration drift:

```bash
python src/manage.py makemigrations --check --dry-run
```

## Ruff policy

The foundation enables:

- E — pycodestyle errors
- F — Pyflakes
- I — import sorting
- UP — pyupgrade
- B — flake8-bugbear

Runtime target is Python 3.12 and line length is 100.

Django-generated migration files are excluded from Ruff ownership. Generated migrations are reviewed
for schema correctness, but are not manually reformatted to satisfy style tools.

## pytest policy

pytest-django uses:

- `DJANGO_SETTINGS_MODULE=config.settings.test`
- `pythonpath = ["src"]`
- `testpaths = ["src/apps", "tests"]`

Existing Django `TestCase` tests are intentionally not rewritten. pytest runs them as-is.

## Shared fixtures

Repository-root `conftest.py` provides only small, reusable domain fixtures:

- `user`
- `published_form`
- `linear_process`

Fixtures should stay composable and small. Gate-specific business scenarios belong with their
own app/service tests rather than growing a global fixture hierarchy.

## Coverage policy

Coverage tooling is available from Gate 2F, but no arbitrary numeric coverage threshold is frozen yet.

A meaningful threshold should be selected after service/API implementation exists; setting a high
percentage now would reward shallow tests against a mostly structural foundation.
