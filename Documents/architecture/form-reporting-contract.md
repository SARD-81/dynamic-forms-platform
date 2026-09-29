# Form Reporting Contract

Status: Gate 3 Issue #36 implementation contract.

## Scope

Form reporting is an owner-only Forms-domain read concern.

This contract covers:

- total non-unique participant view count;
- total Form submissions;
- recent submission activity;
- daily submission timeline;
- Question-level aggregation;
- paginated submitted-response browsing;
- response detail.

It does not include Process reporting, scheduled report delivery, real-time push, or file export.

## Ownership and privacy

All HTML and REST report endpoints require authentication and Form ownership.

Response browsing deliberately does not expose respondent identity, user ID, username, email, or other account fields. A response is classified only as:

- `anonymous`;
- `authenticated`.

The response body contains submitted values and the immutable Question/Option labels needed to interpret them.

## Aggregation semantics

Every Question reports:

- `answered_count`: number of submissions that contain an Answer row for the Question;
- `unanswered_count`: total Form submissions minus `answered_count`.

This makes optional unanswered Questions visible rather than silently changing report denominators.

### TEXT

TEXT reports `answered_count` and `unanswered_count`.

No numeric aggregation is produced. Text values are available only through response browsing.

### NUMBER

NUMBER reports:

- answered count;
- minimum;
- maximum;
- sum;
- average.

Only submissions that answered the Question contribute numeric values.

### SELECT

Each option reports:

- selection count;
- percentage.

The percentage denominator is the number of submissions that answered that SELECT Question, not total Form submissions.

Because SELECT stores one selected option per Answer, option percentages for a non-empty Question normally sum to 100%.

### CHECKBOX

Each option reports:

- selection count;
- percentage.

The percentage denominator is the number of submissions that answered that CHECKBOX Question.

A single Answer may select multiple options, so CHECKBOX option percentages are independent and do not have to sum to 100%.

When no submission answered a SELECT/CHECKBOX Question, every option percentage is `0.00`.

## Query contract

Aggregation is assembled with a constant number of ORM queries across Question count:

- Form submission count;
- recent activity;
- timeline;
- Question schema + prefetched Options;
- Answer aggregation grouped by Question;
- AnswerOption aggregation grouped by Option.

No per-Question database query loop is used.

Response detail prefetches Answer Question data and selected QuestionOptions.

## Cache contract

Django's shared cache layer stores only submission-derived aggregate report data for PUBLISHED/CLOSED Forms.

The live Form row supplies `view_count` on every report request, so participant view increments do not become stale behind report cache.

DRAFT reports are not cached because their schema can still change.

After `submit_form(...)` commits successfully, a `transaction.on_commit()` callback invalidates the Form report aggregate cache. Failed/rolled-back submissions do not publish invalidation callbacks.

Cache failure is best-effort for reporting: reads fall back to PostgreSQL and cache write/delete failure never makes the report unavailable.

PostgreSQL remains the source of truth.

## Owner HTML routes

- `GET /forms/<form_id>/report/`
- `GET /forms/<form_id>/report/responses/`
- `GET /forms/<form_id>/report/responses/<submission_public_id>/`

## Owner REST routes

- `GET /api/v1/forms/<form_id>/report/`
- `GET /api/v1/forms/<form_id>/responses/`
- `GET /api/v1/forms/<form_id>/responses/<submission_public_id>/`

Submission list pagination defaults to 20 rows. REST callers may request `page_size` up to 100.
