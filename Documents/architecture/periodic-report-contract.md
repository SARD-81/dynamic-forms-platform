# Periodic Report Contract — Issue #38

## Purpose

Issue #38 defines one delivery-neutral summary payload consumed later by both EMAIL and API delivery in Issue #40. It contains aggregate platform activity only and intentionally excludes raw answers, private passwords, credentials, respondent PII, and anonymous resume tokens.

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

## Subscription contract

`ReportSubscription` remains the frozen BL-DATA-002 model. No migration is required.

- EMAIL requires a syntactically valid `email` and requires `endpoint_url = NULL`.
- API requires a valid HTTP/HTTPS `endpoint_url` and requires `email = NULL`.
- WEEKLY and MONTHLY are the only frequencies.
- inactive subscriptions are excluded from the due selector.
- a subscription is due when its last successful `last_sent_at` is absent or older than the end of the most recently completed period.

Issue #38 never updates `last_sent_at`. Issue #40 must update it only after successful delivery.

## Authorization

HTML and REST management are restricted to site staff/superusers. Ordinary authenticated users cannot list, create, inspect, edit, deactivate, or preview site-wide reporting subscriptions.

## Issue #40 handoff

Issue #40 should use `get_due_report_subscriptions()` plus `generate_periodic_report_payload()` and must preserve this payload schema for both delivery methods. Runtime sending, retries/backoff, Celery/Beat topology, and delivery success bookkeeping remain out of scope here.
