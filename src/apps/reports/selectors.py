import datetime

from django.db.models import Q
from django.utils import timezone

from .models import ReportSubscription
from .services import ensure_admin_access


def get_report_subscriptions_for_admin(*, user, is_active=None, frequency=None):
    """
    لیست تمام اشتراک‌ها برای ادمین همراه با فیلتر وضعیت و فرکانس.
    """
    ensure_admin_access(user=user)

    qs = ReportSubscription.objects.select_related("created_by").order_by("-created_at", "-id")
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    if frequency is not None:
        qs = qs.filter(frequency=frequency)
    return qs


def get_report_subscription_for_admin(*, subscription_id, user):
    """
    واکشی یک اشتراک مشخص برای ادمین.
    """
    ensure_admin_access(user=user)

    return (
        ReportSubscription.objects.select_related("created_by").filter(pk=subscription_id).first()
    )


def get_due_report_subscriptions(*, frequency, as_of=None):
    """
    سلکتور پایه دامنه‌ای جهت استخراج اشتراک‌های فعال که موعد ارسال آن‌ها فرا رسیده است.
    - WEEKLY: هرگز ارسال نشده یا حداقل ۷ روز از آخرین ارسال گذشته است.
    - MONTHLY: هرگز ارسال نشده یا حداقل ۲۸ روز از آخرین ارسال گذشته است.
    کاملاً ایزوله از لاجیک تولید پی‌لود گزارش‌ها.
    """
    if frequency not in ReportSubscription.Frequency.values:
        raise ValueError(f"Invalid frequency: {frequency}")

    reference_time = as_of or timezone.now()

    if frequency == ReportSubscription.Frequency.WEEKLY:
        cutoff = reference_time - datetime.timedelta(days=7)
    else:
        cutoff = reference_time - datetime.timedelta(days=28)

    return (
        ReportSubscription.objects.filter(
            is_active=True,
            frequency=frequency,
        )
        .filter(Q(last_sent_at__isnull=True) | Q(last_sent_at__lte=cutoff))
        .select_related("created_by")
        .order_by("id")
    )
