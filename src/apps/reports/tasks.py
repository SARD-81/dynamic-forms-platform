import logging
from datetime import datetime

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .delivery import ReportDeliveryError, deliver_report_subscription
from .selectors import get_due_report_subscriptions

logger = logging.getLogger(__name__)


def _parse_as_of(as_of_iso):
    if not as_of_iso:
        return timezone.now()
    parsed = datetime.fromisoformat(as_of_iso)
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


@shared_task(
    bind=True,
    name="apps.reports.tasks.deliver_report_subscription_task",
    max_retries=2,
)
def deliver_report_subscription_task(self, subscription_id, as_of_iso=None):
    as_of = _parse_as_of(as_of_iso)
    try:
        return deliver_report_subscription(
            subscription_id=subscription_id,
            as_of=as_of,
        )
    except ReportDeliveryError as exc:
        retry_count = self.request.retries
        if retry_count >= settings.REPORT_DELIVERY_MAX_RETRIES:
            logger.error(
                "Scheduled report delivery exhausted retries subscription_id=%s",
                subscription_id,
            )
            raise
        delay = min(
            settings.REPORT_DELIVERY_RETRY_DELAY_SECONDS * (2**retry_count),
            settings.REPORT_DELIVERY_RETRY_MAX_DELAY_SECONDS,
        )
        logger.warning(
            "Scheduled report delivery failed; retrying subscription_id=%s retry=%s",
            subscription_id,
            retry_count + 1,
        )
        raise self.retry(
            exc=exc,
            countdown=delay,
            max_retries=settings.REPORT_DELIVERY_MAX_RETRIES,
        ) from exc


@shared_task(name="apps.reports.tasks.dispatch_due_report_subscriptions")
def dispatch_due_report_subscriptions(as_of_iso=None):
    as_of = _parse_as_of(as_of_iso)
    due = get_due_report_subscriptions(as_of=as_of)
    scheduled = 0
    failed_to_schedule = 0

    for subscription in due:
        try:
            deliver_report_subscription_task.delay(
                subscription.pk,
                as_of.isoformat(),
            )
        except Exception:
            failed_to_schedule += 1
            logger.exception(
                "Could not schedule/execute report delivery subscription_id=%s",
                subscription.pk,
            )
            continue
        scheduled += 1

    return {
        "due": len(due),
        "scheduled": scheduled,
        "failed_to_schedule": failed_to_schedule,
    }
