from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import URLValidator, validate_email
from django.db import transaction
from django.utils import timezone

from .models import ReportSubscription
from .periods import report_period_bounds
from .selectors import get_platform_report_activity


def ensure_staff_actor(actor):
    if actor is None or not getattr(actor, "is_authenticated", False):
        raise PermissionDenied("Authentication is required.")
    if not (getattr(actor, "is_staff", False) or getattr(actor, "is_superuser", False)):
        raise PermissionDenied("Site staff access is required.")


def _normalize_target(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def validate_subscription_input(*, frequency, delivery_method, email=None, endpoint_url=None):
    if frequency not in ReportSubscription.Frequency.values:
        raise ValidationError({"frequency": "Unsupported report frequency."})
    if delivery_method not in ReportSubscription.DeliveryMethod.values:
        raise ValidationError({"delivery_method": "Unsupported delivery method."})

    email = _normalize_target(email)
    endpoint_url = _normalize_target(endpoint_url)

    if delivery_method == ReportSubscription.DeliveryMethod.EMAIL:
        if not email:
            raise ValidationError({"email": "An email target is required for EMAIL delivery."})
        if endpoint_url:
            raise ValidationError(
                {"endpoint_url": "API endpoint must be empty for EMAIL delivery."}
            )
        validate_email(email)
        return email, None

    if not endpoint_url:
        raise ValidationError({"endpoint_url": "An endpoint URL is required for API delivery."})
    if email:
        raise ValidationError({"email": "Email target must be empty for API delivery."})
    URLValidator(schemes=["http", "https"])(endpoint_url)
    return None, endpoint_url


@transaction.atomic
def create_report_subscription(
    *, actor, frequency, delivery_method, email=None, endpoint_url=None, is_active=True
):
    ensure_staff_actor(actor)
    email, endpoint_url = validate_subscription_input(
        frequency=frequency,
        delivery_method=delivery_method,
        email=email,
        endpoint_url=endpoint_url,
    )
    return ReportSubscription.objects.create(
        created_by=actor,
        frequency=frequency,
        delivery_method=delivery_method,
        email=email,
        endpoint_url=endpoint_url,
        is_active=bool(is_active),
    )


@transaction.atomic
def update_report_subscription(
    *,
    actor,
    subscription_id,
    frequency,
    delivery_method,
    email=None,
    endpoint_url=None,
    is_active=True,
):
    ensure_staff_actor(actor)
    subscription = ReportSubscription.objects.select_for_update().get(pk=subscription_id)
    email, endpoint_url = validate_subscription_input(
        frequency=frequency,
        delivery_method=delivery_method,
        email=email,
        endpoint_url=endpoint_url,
    )
    subscription.frequency = frequency
    subscription.delivery_method = delivery_method
    subscription.email = email
    subscription.endpoint_url = endpoint_url
    subscription.is_active = bool(is_active)
    subscription.save(
        update_fields=[
            "frequency",
            "delivery_method",
            "email",
            "endpoint_url",
            "is_active",
            "updated_at",
        ]
    )
    return subscription


@transaction.atomic
def deactivate_report_subscription(*, actor, subscription_id):
    ensure_staff_actor(actor)
    subscription = ReportSubscription.objects.select_for_update().get(pk=subscription_id)
    if subscription.is_active:
        subscription.is_active = False
        subscription.save(update_fields=["is_active", "updated_at"])
    return subscription


def generate_periodic_report_payload(*, frequency, as_of=None):
    period_start, period_end = report_period_bounds(frequency=frequency, as_of=as_of)
    generated_at = as_of or timezone.now()
    if timezone.is_naive(generated_at):
        generated_at = timezone.make_aware(generated_at, timezone.get_current_timezone())
    activity = get_platform_report_activity(
        period_start=period_start,
        period_end=period_end,
    )
    return {
        "schema_version": "1.0",
        "frequency": frequency,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "generated_at": generated_at.isoformat(),
        "activity": activity,
    }
