## Summary

Describe the change and why it is needed.

## Related Issue

Closes #

## Gate / Scope

- Gate:
- Subgate:

## Branch target

- [ ] Normal work targets `dev`, or this PR is an explicitly documented `dev → main` milestone promotion.

## Verification

- [ ] Change is within the linked Issue scope.
- [ ] Tests added/updated where needed.
- [ ] Migrations included for model changes.
- [ ] `ruff check .` passes.
- [ ] `ruff format --check .` passes.
- [ ] Test suite passes.
- [ ] Migration drift check passes.
- [ ] No secrets or local-only configuration committed.
- [ ] Frozen baselines were not changed silently.
- [ ] DB constraints are implemented as real constraints where required.
- [ ] Cross-table invariants are enforced in Service code + tests.
- [ ] Business/service code does not read environment variables directly.
- [ ] `forms` does not import `processes`.

## Documentation

- [ ] README/docs updated if behavior, workflow, architecture, or setup changed.
