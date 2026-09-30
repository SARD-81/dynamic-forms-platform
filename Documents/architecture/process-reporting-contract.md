# Process Reporting Contract — Issue #37

## Scope

Issue #37 provides owner-only analytics and run browsing for Process execution. It is read-only and does not change ProcessRun or ProcessStepRun state.

## Process-level completion semantic

A **completed ProcessRun** is the Process-level received-response/completion measure.

- `total_runs`: every ProcessRun started for the Process.
- `completed_runs`: ProcessRuns whose status is `COMPLETED`.
- `in_progress_runs`: `total_runs - completed_runs`.
- `response_count`: equal to `completed_runs`.
- `completion_rate`: `completed_runs / total_runs * 100`, or `0.00` when there are no runs.

HTML and REST use the same semantic.

## Step analytics

For each ProcessStep, reporting exposes the current number of ProcessStepRun rows in `COMPLETED`, `AVAILABLE`, and `LOCKED`. The same model works for LINEAR and FREE Processes.

## Privacy

Run browsing exposes only the identity class: `authenticated` or `anonymous`. Raw resume tokens and `resume_token_hash` are not report fields and are never rendered or serialized.

A linked FormSubmission is exposed only as a safe reference with public ID, submitted timestamp, and identity class. Answer detail remains owned by the Form reporting feature and is reached through the existing owner-only Form response detail route.

## Query and cache contract

- Reporting reads live in `apps.processes.report_selectors`.
- Run lists use annotations for progress counts and avoid per-run queries.
- Run detail prefetches ordered step state, Form, and linked FormSubmission rows.
- Summary cache keys are revisioned from authoritative database state: run count, latest run ID, completed-run count, completed-step count, and latest step completion time.
- Starting a run or completing a step changes the revision, making stale cached summaries unreachable.
- The database remains the source of truth.
- Process `view_count` is read live outside the cached aggregate payload.

## Endpoints

Owner HTML:

- `/processes/<process_id>/report/`
- `/processes/<process_id>/report/runs/`
- `/processes/<process_id>/report/runs/<run_public_id>/`

Owner REST:

- `/api/v1/processes/<process_id>/report/`
- `/api/v1/processes/<process_id>/runs/`
- `/api/v1/processes/<process_id>/runs/<run_public_id>/`

All routes are owner-scoped. Cross-owner access resolves as not found.
