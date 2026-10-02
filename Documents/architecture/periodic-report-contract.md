# Periodic Report Contract — Issues #38 and #40

## Purpose

Issue #38 defines one delivery-neutral summary payload consumed by both EMAIL and API delivery in Issue #40. It contains aggregate platform activity only and intentionally excludes raw answers, private passwords, credentials, respondent PII, and anonymous resume tokens.

Issue #40 adds scheduled delivery around that same payload without changing schema v1.0.

## Period boundaries

Periods are half-open: `period_start <= event < period_end` in the active Django timezone.

- `WEEKLY`: the most recent fully completed ISO-style week, Monday 00:00 through the following Monday 00:00.
- `MONTHLY`: the most recent fully completed calendar month, first day 00:00 through the first day of the following month 00:00.

This keeps retries deterministic: repeated generation during the same current week/month produces the same reporting window.

## Payload schema v1.0

```text
schema_version
frequency
period_start
period_end
generated_at
activity.forms.created
activity.forms.created_current_status.{draft,published,closed}
activity.forms.submissions
activity.processes.created
activity.processes.created_current_status.{draft,published,closed}
activity.processes.runs_started
activity.processes.runs_completed
activity.cumulative_views.{forms,processes}
```

`created_current_status` means the current lifecycle status of objects whose `created_at` falls inside the reporting period. The frozen Form/Process schema has no `published_at` or `closed_at`, so the report must not pretend to count publication/closure transitions that cannot be timestamped accurately.

View counters are cumulative snapshots because the frozen schema stores only aggregate `view_count`, not individual timestamped view events.

## Subscription and due contract

`ReportSubscription` remains the frozen BL-DATA-002 model. No migration is required.

- EMAIL requires a syntactically valid `email` and requires `endpoint_url = NULL`.
- API requires a valid HTTP/HTTPS `endpoint_url` and requires `email = NULL`.
- WEEKLY and MONTHLY are the only frequencies.
- inactive subscriptions are never due.
- a subscription is not due for a reporting period that ended before the subscription existed.
- otherwise a subscription is due when `last_sent_at` is absent or older than the end of the most recently completed period.
- `last_sent_at` is updated only after an external delivery succeeds.

This means a newly-created subscription does not back-send an already-finished reporting period that predates the subscription.

## Scheduled dispatcher

Celery Beat runs `apps.reports.tasks.dispatch_due_report_subscriptions` once per hour. Hourly polling is intentional: the due rule, not the exact Beat wall-clock time, decides whether a WEEKLY or MONTHLY report needs delivery. This also lets a restarted development stack catch up after temporary downtime.

The dispatcher:

1. takes one timezone-aware `as_of` snapshot;
2. finds due active subscriptions;
3. enqueues one independent delivery task per subscription;
4. continues scheduling other subscriptions if one enqueue/eager execution fails.

## Delivery task and retry behavior

`apps.reports.tasks.deliver_report_subscription_task` re-checks due state inside the delivery Service before sending.

Retry policy is bounded:

- maximum retries after the first attempt: 2;
- base retry delay: 30 seconds;
- exponential delays capped at 5 minutes;
- exhausted failures are logged by subscription ID only;
- failed delivery leaves `last_sent_at` unchanged, so the subscription remains due for a later dispatcher run.

Targets, passwords, credentials, raw tokens, and payload PII are not written to task logs.

## Concurrency and delivery semantics

The delivery Service obtains `select_for_update()` on the subscription row and re-checks the due rule while holding that lock. For this bootcamp-scale implementation, the bounded external delivery attempt remains inside that transaction so two workers cannot concurrently send the same subscription/period.

Delivery is **at-least-once**, not globally exactly-once: a process/database failure after an external system accepts a message but before the transaction commits may cause a later retry. API requests therefore include a deterministic `Idempotency-Key` based on subscription ID and reporting-period end so receivers can deduplicate retries.

## EMAIL delivery

EMAIL delivery uses Django's configured email backend and sends both plain-text and HTML summaries. Development uses the console backend, tests use the in-memory backend, and production consumes the CHG-0004 SMTP settings contract.

A send is successful only when Django reports one message sent. `last_sent_at` is then recorded.

## API delivery

API delivery uses an HTTP `POST` with the exact payload schema v1.0 and `Content-Type: application/json`.

- standard-library HTTP client only; no new dependency;
- timeout: 10 seconds;
- only HTTP 2xx is success;
- timeout, transport errors, or non-2xx responses are retryable failures;
- `Idempotency-Key` is sent for receiver-side deduplication;
- `last_sent_at` changes only after success.

## Authorization

HTML and REST management are restricted to site staff/superusers. Ordinary authenticated users cannot list, create, inspect, edit, deactivate, or preview site-wide reporting subscriptions.

## Development runtime

CHG-0003 authorizes and Issue #40 applies two development services in addition to the existing web/PostgreSQL/Redis services:

```text
celery-worker
celery-beat
```

Both reuse the application image and Redis logical DB 1 via `CELERY_BROKER_URL`. Beat uses Celery's default file-backed scheduler; no `django-celery-beat`, result backend, extra Redis service, model change, or production topology is introduced.
