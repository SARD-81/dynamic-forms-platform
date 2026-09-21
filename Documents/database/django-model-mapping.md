# BL-DATA-002 — Django Model Mapping

**Gate:** 2D — Frozen Data Models & Migration Foundation  
**Status:** IMPLEMENTATION IN PROGRESS  
**Source baseline:** BL-DATA-002

## Entity count

BL-DATA-002 defines 14 persisted entities total.

- 1 existing bootstrap model: `accounts.User`
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

These remain explicit future Service-layer rules:

1. `ProcessStepRun.process_step.process_id == ProcessStepRun.process_run.process_id`
2. `ProcessStepRun.submission.form_id == ProcessStepRun.process_step.form_id`
3. `AnswerOption.option.question_id == Answer.question_id`
4. `Answer.question.form_id == FormSubmission.form_id`

They cross table boundaries and therefore are not represented as ordinary row-local PostgreSQL CHECK constraints.

## Migration policy

Django migration files are per application. Gate 2D therefore does **not** attempt to create one artificial migration file for all apps.

Correct sequence:

1. complete all 14 model definitions;
2. run one `makemigrations` operation for all project apps;
3. inspect the complete initial dependency graph;
4. run Django checks;
5. only then execute the first project `migrate`.

No project migration is to be applied incrementally app-by-app before the complete initial graph exists.


## ProcessRun respondent deletion policy clarification

The Gate 2D implementation uses:

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

Using `SET_NULL` for `respondent` would turn an authenticated historical run into:

- `respondent_id IS NULL`
- `resume_token_hash IS NULL`

which violates the frozen XOR identity constraint. PostgreSQL would therefore reject such a delete anyway.

`PROTECT` makes that policy explicit at the ORM boundary and preserves historical identity integrity.

This note is a documentation clarification of the implementation rationale. It does not introduce a new entity, field, relationship, or baseline semantic change.
