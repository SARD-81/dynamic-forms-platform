from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import EmailValidator, URLValidator
from django.db import transaction
from django.utils import timezone

from .models import ReportSubscription

_UNSET = object()

email_validator = EmailValidator()
url_validator = URLValidator(schemes=["http", "https"])


def ensure_admin_access(*, user):
    """
    اعتبارسنجی دسترسی مدیر: فقط کاربران staff یا superuser مجاز به مدیریت اشتراک‌ها هستند.
    کاربران عادی و ناشناس بدون استثنا رد می‌شوند.
    """
    if (
        user is None
        or not getattr(user, "is_authenticated", False)
        or not (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
    ):
        raise PermissionDenied("Only staff members or superusers can manage report subscriptions.")


def _clean_and_validate_subscription_targets(
    *,
    delivery_method,
    email,
    endpoint_url,
):
    cleaned_email = email.strip() if isinstance(email, str) else email
    if cleaned_email == "":
        cleaned_email = None

    cleaned_url = endpoint_url.strip() if isinstance(endpoint_url, str) else endpoint_url
    if cleaned_url == "":
        cleaned_url = None

    errors = {}

    if delivery_method not in ReportSubscription.DeliveryMethod.values:
        errors["delivery_method"] = [
            f"Select a valid delivery method. Choices are: "
            f"{', '.join(ReportSubscription.DeliveryMethod.values)}."
        ]

    # اعتبارسنجی منطق XOR: باید دقیقاً یکی از دو مقصد مشخص شده باشد
    if cleaned_email and cleaned_url:
        errors["delivery_target"] = [
            "Cannot specify both email and endpoint URL. Choose exactly one delivery target."
        ]
    elif not cleaned_email and not cleaned_url:
        errors["delivery_target"] = [
            "A delivery target is required. Provide either an email or an endpoint URL."
        ]

    # تطابق روش تحویل با مقصد و فرمت آن
    if delivery_method == ReportSubscription.DeliveryMethod.EMAIL:
        if cleaned_url:
            errors.setdefault("endpoint_url", []).append(
                "Endpoint URL must not be set when delivery method is EMAIL."
            )
        if not cleaned_email:
            errors.setdefault("email", []).append(
                "Email address is required when delivery method is EMAIL."
            )
        else:
            try:
                email_validator(cleaned_email)
            except ValidationError:
                errors.setdefault("email", []).append("Enter a valid email address.")

    elif delivery_method == ReportSubscription.DeliveryMethod.API:
        if cleaned_email:
            errors.setdefault("email", []).append(
                "Email must not be set when delivery method is API."
            )
        if not cleaned_url:
            errors.setdefault("endpoint_url", []).append(
                "Endpoint URL is required when delivery method is API."
            )
        else:
            try:
                url_validator(cleaned_url)
            except ValidationError:
                errors.setdefault("endpoint_url", []).append("Enter a valid URL.")

    if errors:
        raise ValidationError(errors)

    return cleaned_email, cleaned_url


def _validate_frequency(frequency):
    if frequency not in ReportSubscription.Frequency.values:
        raise ValidationError(
            {
                "frequency": [
                    f"Select a valid frequency. Choices are: "
                    f"{', '.join(ReportSubscription.Frequency.values)}."
                ]
            }
        )


def create_report_subscription(
    *,
    user,
    frequency,
    delivery_method,
    email=None,
    endpoint_url=None,
    is_active=True,
):
    """
    ایجاد اشتراک جدید گزارش‌گیری دوره‌ای با اعتبارسنجی کامل دسترسی و قوانین XOR.
    """
    ensure_admin_access(user=user)
    _validate_frequency(frequency)
    cleaned_email, cleaned_url = _clean_and_validate_subscription_targets(
        delivery_method=delivery_method,
        email=email,
        endpoint_url=endpoint_url,
    )

    with transaction.atomic():
        return ReportSubscription.objects.create(
            created_by=user,
            frequency=frequency,
            delivery_method=delivery_method,
            email=cleaned_email,
            endpoint_url=cleaned_url,
            is_active=bool(is_active),
        )


def update_report_subscription(
    *,
    subscription_id,
    user,
    frequency=_UNSET,
    delivery_method=_UNSET,
    email=_UNSET,
    endpoint_url=_UNSET,
    is_active=_UNSET,
):
    """
    بروزرسانی اتمیک اشتراک موجود با اعتبارسنجی مجدد وضعیت نهایی مدل.
    """
    ensure_admin_access(user=user)

    with transaction.atomic():
        try:
            subscription = ReportSubscription.objects.select_for_update().get(pk=subscription_id)
        except ReportSubscription.DoesNotExist:
            raise ValidationError({"subscription": ["Report subscription not found."]}) from None

        next_frequency = subscription.frequency if frequency is _UNSET else frequency
        next_delivery_method = (
            subscription.delivery_method if delivery_method is _UNSET else delivery_method
        )
        next_email = subscription.email if email is _UNSET else email
        next_endpoint_url = subscription.endpoint_url if endpoint_url is _UNSET else endpoint_url
        next_is_active = subscription.is_active if is_active is _UNSET else bool(is_active)

        _validate_frequency(next_frequency)
        cleaned_email, cleaned_url = _clean_and_validate_subscription_targets(
            delivery_method=next_delivery_method,
            email=next_email,
            endpoint_url=next_endpoint_url,
        )

        subscription.frequency = next_frequency
        subscription.delivery_method = next_delivery_method
        subscription.email = cleaned_email
        subscription.endpoint_url = cleaned_url
        subscription.is_active = next_is_active

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


def deactivate_report_subscription(*, subscription_id, user):
    """
    غیرفعال‌سازی ایمن اشتراک.
    """
    ensure_admin_access(user=user)

    with transaction.atomic():
        try:
            subscription = ReportSubscription.objects.select_for_update().get(pk=subscription_id)
        except ReportSubscription.DoesNotExist:
            raise ValidationError({"subscription": ["Report subscription not found."]}) from None

        if subscription.is_active:
            subscription.is_active = False
            subscription.save(update_fields=["is_active", "updated_at"])
        return subscription


def activate_report_subscription(*, subscription_id, user):
    """
    فعال‌سازی مجدد اشتراک غیرفعال شده.
    """
    ensure_admin_access(user=user)

    with transaction.atomic():
        try:
            subscription = ReportSubscription.objects.select_for_update().get(pk=subscription_id)
        except ReportSubscription.DoesNotExist:
            raise ValidationError({"subscription": ["Report subscription not found."]}) from None

        if not subscription.is_active:
            subscription.is_active = True
            subscription.save(update_fields=["is_active", "updated_at"])
        return subscription


def record_subscription_sent(*, subscription_id, sent_at=None):
    """
    ثبت زمان آخرین ارسال گزارش برای استفاده در رانتایم زمان‌بندی (#40).
    """
    with transaction.atomic():
        subscription = ReportSubscription.objects.select_for_update().get(pk=subscription_id)
        subscription.last_sent_at = sent_at or timezone.now()
        subscription.save(update_fields=["last_sent_at", "updated_at"])
        return subscription
