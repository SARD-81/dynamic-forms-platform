from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import ReportSubscription


def report_period_bounds(*, frequency, as_of=None):
    if frequency not in ReportSubscription.Frequency.values:
        raise ValidationError({"frequency": "Unsupported report frequency."})

    as_of = as_of or timezone.now()
    if timezone.is_naive(as_of):
        as_of = timezone.make_aware(as_of, timezone.get_current_timezone())
    local_as_of = timezone.localtime(as_of)

    if frequency == ReportSubscription.Frequency.WEEKLY:
        period_end = local_as_of.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_end - timedelta(days=period_end.weekday())
        period_start = period_end - timedelta(days=7)
        return period_start, period_end

    period_end = local_as_of.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period_end.month == 1:
        period_start = period_end.replace(year=period_end.year - 1, month=12)
    else:
        period_start = period_end.replace(month=period_end.month - 1)
    return period_start, period_end
