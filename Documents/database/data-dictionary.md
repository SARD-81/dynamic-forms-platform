# BL-DATA-002 — Data Dictionary

**Status:** FROZEN  
**Supersedes:** BL-DATA-001 through CHG-0001  
**Date:** 2026-09-20  
**Timezone:** `USE_TZ=True`; persisted timestamps are timezone-aware UTC.

## Global conventions

Ordering is 1-based:

- `Question.order >= 1`
- `QuestionOption.order >= 1`
- `ProcessStep.order >= 1`

## User

Custom Django user from the first migration. Email is unique.

## OTPChallenge

Fields include user, purpose, code hash, expiry, attempt count, created timestamp, and nullable `verified_at`.

Rules:

- raw OTP is never stored;
- `verified_at` is the single source of truth for successful consumption;
- `attempt_count >= 0`;
- expiry, maximum attempts, cooldown, and latest-valid challenge are Service rules.

## core.Category

User-owned category shared by Form and Process.

- unique per `(owner, name)`;
- optional on Form and Process;
- `core` must remain limited to truly shared concepts.

## Form

Fields include public UUID, owner, optional category, title, description, visibility, optional password hash, status, view count, and timestamps.

Lifecycle:

- `DRAFT -> PUBLISHED -> CLOSED`;
- schema is immutable after publication;
- CLOSED accepts no new direct or process-driven Submission;
- normal closure is blocked while an active ProcessRun depends on the Form;
- runtime submission still re-checks Form availability.

`view_count` is a non-unique page-view counter and is incremented atomically.

Hard-delete policy:

- unused DRAFT may be deleted;
- PUBLISHED/CLOSED is not normally hard-deleted;
- history is protected.

## Question

Types:

- TEXT
- NUMBER
- SELECT
- CHECKBOX

Important rules:

- `UNIQUE(form, order)`;
- `order >= 1`;
- numeric bounds use `Decimal(18,6)`;
- when both bounds exist, min <= max;
- SELECT/CHECKBOX require options before publish;
- TEXT/NUMBER do not own options.

## QuestionOption

- `UNIQUE(question, order)`
- `UNIQUE(question, label)`
- `order >= 1`

## FormSubmission

One completed response.

- public UUID;
- Form FK;
- nullable respondent FK for anonymous submissions;
- submitted timestamp;
- **no Process/ProcessRun/ProcessStep FK**.

Process integration is owned by `ProcessStepRun.submission`.

## Answer

One logical answer per `(submission, question)`.

Representation:

| Question type | Representation |
|---|---|
| TEXT | `text_value` only |
| NUMBER | `number_value` only |
| SELECT | exactly one AnswerOption |
| CHECKBOX | AnswerOption rows according to required/optional rule |

Service invariant:

`Answer.question.form_id == Answer.submission.form_id`.

## AnswerOption

- `UNIQUE(answer, option)`
- Service invariant: `option.question_id == answer.question_id`.

## Process

Workflow containing Forms.

Types:

- LINEAR
- FREE

Lifecycle:

- `DRAFT -> PUBLISHED -> CLOSED`;
- step schema immutable after publish;
- CLOSED blocks new ProcessRun;
- existing IN_PROGRESS runs may continue while required Forms remain available.

## ProcessStep

- `UNIQUE(process, order)`
- `UNIQUE(process, form)`
- `order >= 1`
- Process and Form owner must match;
- Form must be PUBLISHED at configuration time;
- PUBLIC Process may reference only PUBLIC Form.

## ProcessRun

One execution instance.

Identity is exactly one mode:

Authenticated:
- `respondent_id != NULL`
- `resume_token_hash = NULL`

Anonymous:
- `respondent_id = NULL`
- `resume_token_hash != NULL`

`public_id` is an identifier, not a credential.

The raw resume token is high entropy, returned only to the client, and never stored. A deterministic cryptographic digest is persisted so equality/uniqueness checks can be enforced.

Non-null token digests are unique.

Status:

- IN_PROGRESS => `completed_at IS NULL`
- COMPLETED => `completed_at IS NOT NULL`

The same user may run the same Process multiple times.

## ProcessStepRun

Owns the link between a Process execution step and a FormSubmission.

Fields:

- process_run FK;
- process_step FK;
- nullable unique submission FK / OneToOne;
- status;
- nullable completed timestamp.

DB rules:

- `UNIQUE(process_run, process_step)`;
- submission is unique when present;
- COMPLETED requires submission + completed timestamp;
- LOCKED/AVAILABLE require both to be null.

Service-only cross-table rules:

- `process_step.process_id == process_run.process_id`;
- `submission.form_id == process_step.form_id`.

LINEAR:

- first eligible incomplete step AVAILABLE;
- later steps LOCKED;
- no skipping.

FREE:

- incomplete steps may be AVAILABLE in any order.

Step completion is atomic with submission/answers, state change, next-step unlock, and possible ProcessRun completion.

## ReportSubscription

Site-wide periodic report configuration.

- frequency: WEEKLY / MONTHLY;
- delivery: EMAIL / API;
- EMAIL uses email only;
- API uses endpoint URL only.

Per-Form/per-Process subscriptions are outside this baseline.

## Reporting data

Reports are read models over source entities. PostgreSQL business records are the source of truth; Redis may cache computed results.
