# Quality and Test Foundation

**Gate:** 2F — Quality & Test Foundation  
**Status:** COMPLETED / PASSED  
**Target baseline:** BL-FOUNDATION-001

## Standard commands

Install runtime + development dependencies:

```bash
python -m pip install -r requirements/dev.txt
```

Run lint and format checks:

```bash
ruff check .
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

Existing Django `TestCase` constraint tests run unchanged under pytest.

A foundation settings-contract test also verifies that pytest sees:

- `DEBUG=False`;
- Celery in-memory broker;
- local-memory email backend.

## Docker test isolation

The Docker web service intentionally does not export `DJANGO_SETTINGS_MODULE`.

That keeps this command correct:

```bash
docker compose exec web pytest
```

pytest therefore resolves `config.settings.test` from `pyproject.toml` rather than inheriting the
development settings module from the running web service.

## Shared fixtures

Repository-root `conftest.py` provides small, reusable domain fixtures:

- `user`
- `published_form`
- `linear_process`

Fixtures should stay composable and small.

## Coverage policy

Coverage tooling is available, but no arbitrary numeric threshold is frozen yet.

An early foundation run observed 83% coverage. That number is evidence, not a required threshold.
A meaningful threshold should be selected after service/API implementation exists.
