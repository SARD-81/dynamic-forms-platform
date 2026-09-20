# BL-DATA-002 — Domain & Data Architecture Baseline

**Status:** FROZEN  
**Approved:** 2026-09-20  
**Gate:** GATE 1 — Domain & Data Architecture  
**Gate status:** CLOSED  
**Supersedes:** BL-DATA-001  
**Change record:** CHG-0001  
**Architecture dependency:** BL-ARCH-001

## Decision

BL-DATA-002 is the authoritative data baseline.

Source of truth:

- `Documents/database/erd.nomnoml`

Supporting records:

- `Documents/database/data-dictionary.md`
- `Documents/database/constraint-matrix.md`
- `Documents/project-control/change-records/CHG-0001.md`

## Frozen integrity summary

- `UNIQUE(ProcessStepRun.process_run_id, ProcessStepRun.process_step_id)`.
- `ProcessStepRun.submission_id` is nullable + unique and is owned by ProcessStepRun.
- FormSubmission has no direct Process/ProcessRun/ProcessStep FK.
- `ProcessStepRun.process_step.process_id == ProcessStepRun.process_run.process_id` — Service-only.
- `ProcessStepRun.submission.form_id == ProcessStepRun.process_step.form_id` — Service-only.
- `UNIQUE(AnswerOption.answer_id, AnswerOption.option_id)`.
- `AnswerOption.option.question_id == Answer.question_id` — Service-only.
- `Answer.question.form_id == FormSubmission.form_id` — Service-only.
- ProcessRun identity is authenticated respondent XOR anonymous resume-token digest.
- non-null resume-token digests are unique.
- ProcessRun/ProcessStepRun state-data consistency is DB + Service enforced.
- Question, QuestionOption, and ProcessStep order values start at 1.

## Lifecycle summary

Form:

- `DRAFT -> PUBLISHED -> CLOSED`
- schema immutable after publish
- CLOSED accepts no new Submission, including process-driven Submission
- normal closure blocked while active runs depend on Form
- PUBLISHED/CLOSED not hard-deleted in normal product flow

Process:

- `DRAFT -> PUBLISHED -> CLOSED`
- step schema immutable after publish
- CLOSED blocks new ProcessRun
- existing IN_PROGRESS runs may continue while required Forms remain available

## Data semantics

- numeric fields: `Decimal(18,6)`
- `USE_TZ=True`; timezone-aware UTC persistence
- `view_count`: non-unique page views
- shared category model: `core.Category`
- ReportSubscription: site-wide, EMAIL/API

## CHANGES

- Applied CHG-0001 to make ProcessStepRun/Submission ownership, uniqueness, ProcessRun identity/state constraints, and AnswerOption uniqueness explicit.
- Standardized 1-based ordering and clarified closed-Form, deletion, category naming, and cross-table Service-only policies.

## Change control

No silent edits. A later structural or semantic change requires a new `CHG-XXXX` and, if approved, a superseding data baseline.

**GATE 1 — CLOSED**
