from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Max, Prefetch, Q

from .models import Process, ProcessRun, ProcessStepRun
from .report_cache import get_cached_process_report, set_cached_process_report
from .selectors import get_process_for_owner

PROCESS_REPORT_RECENT_LIMIT = 5
PROCESS_REPORT_PAGE_SIZE = 20


def _percentage(*, count, denominator):
    if not denominator:
        return Decimal("0.00")
    return ((Decimal(count) * Decimal("100")) / Decimal(denominator)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _process_report_revision(*, process):
    run_revision = ProcessRun.objects.filter(process_id=process.pk).aggregate(
        run_count=Count("id"),
        latest_run_id=Max("id"),
        completed_run_count=Count(
            "id",
            filter=Q(status=ProcessRun.Status.COMPLETED),
        ),
    )
    step_revision = ProcessStepRun.objects.filter(process_run__process_id=process.pk).aggregate(
        completed_step_count=Count(
            "id",
            filter=Q(status=ProcessStepRun.Status.COMPLETED),
        ),
        latest_step_completed_at=Max("completed_at"),
    )
    return {
        "process_public_id": process.public_id,
        **run_revision,
        **step_revision,
    }


def _build_process_aggregate(*, process, revision):
    total_runs = revision["run_count"]
    completed_runs = revision["completed_run_count"]
    in_progress_runs = total_runs - completed_runs

    recent_activity = [
        {
            "public_id": row["public_id"],
            "status": row["status"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "respondent_type": (
                "authenticated" if row["respondent_id"] is not None else "anonymous"
            ),
        }
        for row in ProcessRun.objects.filter(process_id=process.pk)
        .order_by("-started_at", "-id")
        .values(
            "public_id",
            "status",
            "started_at",
            "completed_at",
            "respondent_id",
        )[:PROCESS_REPORT_RECENT_LIMIT]
    ]

    distributions = {}
    rows = (
        ProcessStepRun.objects.filter(process_run__process_id=process.pk)
        .values("process_step_id", "status")
        .annotate(count=Count("id"))
    )
    for row in rows:
        distributions.setdefault(row["process_step_id"], {})[row["status"]] = row["count"]

    steps = []
    for step in process.steps.all():
        counts = distributions.get(step.pk, {})
        steps.append(
            {
                "id": step.pk,
                "order": step.order,
                "form_id": step.form_id,
                "form_public_id": step.form.public_id,
                "form_title": step.form.title,
                "completed_count": counts.get(ProcessStepRun.Status.COMPLETED, 0),
                "available_count": counts.get(ProcessStepRun.Status.AVAILABLE, 0),
                "locked_count": counts.get(ProcessStepRun.Status.LOCKED, 0),
            }
        )

    return {
        "total_runs": total_runs,
        "completed_runs": completed_runs,
        "in_progress_runs": in_progress_runs,
        "response_count": completed_runs,
        "completion_rate": _percentage(count=completed_runs, denominator=total_runs),
        "completion_semantic": (
            "Completed ProcessRuns are the Process-level response/completion measure."
        ),
        "recent_activity": recent_activity,
        "steps": steps,
    }


def get_process_report_summary(*, owner, process_id):
    process = get_process_for_owner(owner=owner, process_id=process_id)
    if process is None:
        return None

    revision = _process_report_revision(process=process)
    aggregate = None
    if process.status != Process.Status.DRAFT:
        aggregate = get_cached_process_report(**revision)

    if aggregate is None:
        aggregate = _build_process_aggregate(process=process, revision=revision)
        if process.status != Process.Status.DRAFT:
            set_cached_process_report(payload=aggregate, **revision)

    return {
        "id": process.pk,
        "public_id": process.public_id,
        "title": process.title,
        "status": process.status,
        "process_type": process.process_type,
        "visibility": process.visibility,
        "view_count": process.view_count,
        **aggregate,
    }


def get_process_report_runs(*, owner, process_id):
    return (
        ProcessRun.objects.filter(process_id=process_id, process__owner=owner)
        .select_related("respondent")
        .defer("resume_token_hash")
        .annotate(
            total_steps=Count("step_runs"),
            completed_steps=Count(
                "step_runs",
                filter=Q(step_runs__status=ProcessStepRun.Status.COMPLETED),
            ),
        )
        .order_by("-started_at", "-id")
    )


def process_run_list_item(run):
    return {
        "public_id": run.public_id,
        "status": run.status,
        "respondent_type": ("authenticated" if run.respondent_id is not None else "anonymous"),
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "completed_steps": run.completed_steps,
        "total_steps": run.total_steps,
    }


def get_process_report_run_detail(*, owner, process_id, run_public_id):
    step_queryset = ProcessStepRun.objects.select_related(
        "process_step",
        "process_step__form",
        "submission",
    ).order_by("process_step__order", "id")

    run = (
        ProcessRun.objects.filter(
            process_id=process_id,
            process__owner=owner,
            public_id=run_public_id,
        )
        .select_related("process", "respondent")
        .defer("resume_token_hash")
        .prefetch_related(
            Prefetch(
                "step_runs",
                queryset=step_queryset,
                to_attr="report_step_runs",
            )
        )
        .first()
    )
    if run is None:
        return None

    return {
        "public_id": run.public_id,
        "status": run.status,
        "respondent_type": ("authenticated" if run.respondent_id is not None else "anonymous"),
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "steps": [
            {
                "step_id": step_run.process_step_id,
                "order": step_run.process_step.order,
                "status": step_run.status,
                "completed_at": step_run.completed_at,
                "form_id": step_run.process_step.form_id,
                "form_public_id": step_run.process_step.form.public_id,
                "form_title": step_run.process_step.form.title,
                "submission": (
                    {
                        "public_id": step_run.submission.public_id,
                        "submitted_at": step_run.submission.submitted_at,
                        "respondent_type": (
                            "authenticated"
                            if step_run.submission.respondent_id is not None
                            else "anonymous"
                        ),
                    }
                    if step_run.submission_id is not None
                    else None
                ),
            }
            for step_run in run.report_step_runs
        ],
    }
