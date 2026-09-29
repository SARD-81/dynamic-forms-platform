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

- authoritative submission revision (`COUNT(id)` + `MAX(id)`), with the count reused as `total_submissions`;
- recent activity;
- timeline;
- Question schema + prefetched Options;
- Answer aggregation grouped by Question;
- AnswerOption aggregation grouped by Option.

No per-Question database query loop is used. The authoritative revision query replaces a separate submission-count query, so revision safety does not add a query to the cache-miss aggregation path.

Response detail prefetches Answer Question data and selected QuestionOptions.

## Cache contract

Django's shared cache layer stores only submission-derived aggregate report data for PUBLISHED/CLOSED Forms.

The live Form row supplies `view_count` on every report request, so participant view increments do not become stale behind report cache.

DRAFT reports are not cached because their schema can still change.

For PUBLISHED/CLOSED Forms, every report summary read first obtains an authoritative submission revision from PostgreSQL: `COUNT(FormSubmission.id)` plus `MAX(FormSubmission.id)`. The immutable Form `public_id` and this revision are both part of the cache key.

A newly committed submission therefore changes the cache identity before the next report read. An older cached aggregate cannot be selected again, even if Redis was unavailable when cleanup ran and the stale entry is still physically present.

After `submit_form(...)` commits successfully, a `transaction.on_commit()` callback still deletes the previous revision key as best-effort cleanup. Failed/rolled-back submissions do not publish cleanup callbacks. Cleanup failure affects only temporary cache storage; old revision keys remain unreachable and expire through the normal five-minute TTL.

Cache read/write failure remains best-effort for reporting: reads fall back to PostgreSQL and cache failures never make the report unavailable.

PostgreSQL remains the source of truth for both report data and cache revision identity.

## Owner HTML routes

- `GET /forms/<form_id>/report/`
- `GET /forms/<form_id>/report/responses/`
- `GET /forms/<form_id>/report/responses/<submission_public_id>/`

## Owner REST routes

- `GET /api/v1/forms/<form_id>/report/`
- `GET /api/v1/forms/<form_id>/responses/`
- `GET /api/v1/forms/<form_id>/responses/<submission_public_id>/`

Submission list pagination defaults to 20 rows. REST callers may request `page_size` up to 100.
