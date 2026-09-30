from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from apps.forms.models import Form, FormSubmission
from apps.processes.models import Process, ProcessRun

from .models import ReportSubscription


def get_report_subscriptions():
    return ReportSubscription.objects.select_related("created_by").order_by("-created_at", "-id")


def get_report_subscription(*, subscription_id):
    return get_report_subscriptions().filter(pk=subscription_id).first()


def get_platform_report_activity(*, period_start, period_end):
    period_forms = Form.objects.filter(created_at__gte=period_start, created_at__lt=period_end)
    form_counts = period_forms.aggregate(
        created=Count("id"),
        draft=Count("id", filter=Q(status=Form.Status.DRAFT)),
        published=Count("id", filter=Q(status=Form.Status.PUBLISHED)),
        closed=Count("id", filter=Q(status=Form.Status.CLOSED)),
    )
    period_processes = Process.objects.filter(
        created_at__gte=period_start,
        created_at__lt=period_end,
    )
    process_counts = period_processes.aggregate(
        created=Count("id"),
        draft=Count("id", filter=Q(status=Process.Status.DRAFT)),
        published=Count("id", filter=Q(status=Process.Status.PUBLISHED)),
        closed=Count("id", filter=Q(status=Process.Status.CLOSED)),
    )

    form_submissions = FormSubmission.objects.filter(
        submitted_at__gte=period_start,
        submitted_at__lt=period_end,
    ).count()
    runs_started = ProcessRun.objects.filter(
        started_at__gte=period_start,
        started_at__lt=period_end,
    ).count()
    runs_completed = ProcessRun.objects.filter(
        completed_at__gte=period_start,
        completed_at__lt=period_end,
    ).count()

    form_views = Form.objects.aggregate(total=Coalesce(Sum("view_count"), 0))["total"]
    process_views = Process.objects.aggregate(total=Coalesce(Sum("view_count"), 0))["total"]

    return {
        "forms": {
            "created": form_counts["created"],
            "created_current_status": {
                "draft": form_counts["draft"],
                "published": form_counts["published"],
                "closed": form_counts["closed"],
            },
            "submissions": form_submissions,
        },
        "processes": {
            "created": process_counts["created"],
            "created_current_status": {
                "draft": process_counts["draft"],
                "published": process_counts["published"],
                "closed": process_counts["closed"],
            },
            "runs_started": runs_started,
            "runs_completed": runs_completed,
        },
        "cumulative_views": {
            "forms": form_views,
            "processes": process_views,
        },
    }


def get_due_report_subscriptions(*, as_of=None):
    from .services import report_period_bounds

    due = []
    for subscription in get_report_subscriptions().filter(is_active=True):
        _, period_end = report_period_bounds(frequency=subscription.frequency, as_of=as_of)
        if subscription.last_sent_at is None or subscription.last_sent_at < period_end:
            due.append(subscription)
    return due
