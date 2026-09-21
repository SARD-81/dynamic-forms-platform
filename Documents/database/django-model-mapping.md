# BL-DATA-002 — Django Model Mapping

**Gate:** 2D — Frozen Data Models & Migration Foundation  
**Status:** COMPLETED / VERIFIED  
**Source baseline:** BL-DATA-002

## Entity count

BL-DATA-002 defines 14 persisted entities total.

- 1 bootstrap model: `accounts.User`
- 13 additional persisted models implemented in Gate 2D

## Dependency direction

```text
accounts
   ↓
 core
   ↓
 forms
   ↓
processes

reports → accounts / forms / processes
```

Critical rule:

`forms` never imports or references `processes`.

## DB-enforced rules implemented in models

The ORM definitions use real `models.CheckConstraint(condition=...)`,
`models.UniqueConstraint(...)`, `OneToOneField`, and indexes.

Django 5.2 uses the `condition=` keyword for `CheckConstraint`.

## Service-only invariants intentionally NOT encoded as database CHECK constraints

These remain Service-layer rules:

1. `ProcessStepRun.process_step.process_id == ProcessStepRun.process_run.process_id`
2. `ProcessStepRun.submission.form_id == ProcessStepRun.process_step.form_id`
3. `AnswerOption.option.question_id == Answer.question_id`
4. `Answer.question.form_id == FormSubmission.form_id`

They cross table boundaries and therefore are not represented as ordinary row-local PostgreSQL
CHECK constraints.

## Migration implementation record

Gate 2D completed the initial per-app migration graph after all 14 model definitions existed.

The completed sequence was:

1. complete model definitions;
2. generate migrations for all project apps;
3. inspect the complete dependency graph;
4. run Django checks;
5. verify zero migration drift;
6. apply the first project migration graph in Gate 2E.

Gate 2E then applied the graph successfully to PostgreSQL and verified database constraints.

## ProcessRun respondent deletion policy clarification

The implementation uses:

```python
respondent = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.PROTECT,
    null=True,
    blank=True,
    related_name="process_runs",
)
```

This is intentional.

For an authenticated ProcessRun, the frozen identity invariant is:

- `respondent_id IS NOT NULL`
- `resume_token_hash IS NULL`

Using `SET_NULL` would create an invalid historical identity state. `PROTECT` preserves the
frozen XOR identity invariant.

This note is an implementation clarification and does not change BL-DATA-002.
