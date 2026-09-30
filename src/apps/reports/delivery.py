import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.utils import timezone
from django.utils.html import escape

from .models import ReportSubscription
from .selectors import is_report_subscription_due
from .services import generate_periodic_report_payload


class ReportDeliveryError(Exception):
    """A retryable external report-delivery failure."""


def _delivery_key(*, subscription_id, period_end):
    return f"dynamic-forms-report:{subscription_id}:{period_end}"


def _render_email_content(payload):
    forms = payload["activity"]["forms"]
    processes = payload["activity"]["processes"]
    views = payload["activity"]["cumulative_views"]
    subject = (
        f"Dynamic Forms {payload['frequency'].title()} report — "
        f"{payload['period_start'][:10]} to {payload['period_end'][:10]}"
    )
    text = "\n".join(
        [
            subject,
            "",
            f"Forms created: {forms['created']}",
            f"Form submissions: {forms['submissions']}",
            f"Processes created: {processes['created']}",
            f"Process runs started: {processes['runs_started']}",
            f"Process runs completed: {processes['runs_completed']}",
            f"Cumulative form views: {views['forms']}",
            f"Cumulative process views: {views['processes']}",
            "",
            f"Generated at: {payload['generated_at']}",
        ]
    )
    html = (
        f"<h1>{escape(subject)}</h1>"
        "<ul>"
        f"<li>Forms created: {forms['created']}</li>"
        f"<li>Form submissions: {forms['submissions']}</li>"
        f"<li>Processes created: {processes['created']}</li>"
        f"<li>Process runs started: {processes['runs_started']}</li>"
        f"<li>Process runs completed: {processes['runs_completed']}</li>"
        f"<li>Cumulative form views: {views['forms']}</li>"
        f"<li>Cumulative process views: {views['processes']}</li>"
        "</ul>"
        f"<p>Generated at: {escape(payload['generated_at'])}</p>"
    )
    return subject, text, html


def _deliver_email(*, subscription, payload):
    subject, text, html = _render_email_content(payload)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[subscription.email],
    )
    message.attach_alternative(html, "text/html")
    try:
        sent_count = message.send(fail_silently=False)
    except Exception as exc:
        raise ReportDeliveryError("Email delivery failed.") from exc
    if sent_count != 1:
        raise ReportDeliveryError("Email backend did not confirm delivery.")


def _deliver_api(*, subscription, payload):
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    request = Request(
        subscription.endpoint_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "dynamic-forms-platform/1.0",
            "Idempotency-Key": _delivery_key(
                subscription_id=subscription.pk,
                period_end=payload["period_end"],
            ),
        },
    )
    try:
        with urlopen(
            request,
            timeout=settings.REPORT_API_DELIVERY_TIMEOUT_SECONDS,
        ) as response:
            status_code = getattr(response, "status", None)
            if status_code is None:
                status_code = response.getcode()
    except HTTPError as exc:
        raise ReportDeliveryError(f"API delivery returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ReportDeliveryError("API delivery failed.") from exc
    if not 200 <= status_code < 300:
        raise ReportDeliveryError(f"API delivery returned HTTP {status_code}.")


@transaction.atomic
def deliver_report_subscription(*, subscription_id, as_of=None):
    """Deliver one due period while serializing competing workers on the subscription row.

    The database row lock intentionally spans the bounded external delivery attempt. This keeps the
    Gate 3 implementation simple and prevents two workers from sending the same subscription at the
    same time. Delivery is at-least-once across process/database failures; API receivers also
    receive a deterministic Idempotency-Key for the subscription/reporting period.
    """

    subscription = ReportSubscription.objects.select_for_update().get(pk=subscription_id)
    as_of = as_of or timezone.now()
    if not is_report_subscription_due(subscription=subscription, as_of=as_of):
        reason = "inactive" if not subscription.is_active else "not_due"
        return {"status": "skipped", "reason": reason, "subscription_id": subscription.pk}

    payload = generate_periodic_report_payload(
        frequency=subscription.frequency,
        as_of=as_of,
    )
    if subscription.delivery_method == ReportSubscription.DeliveryMethod.EMAIL:
        _deliver_email(subscription=subscription, payload=payload)
    elif subscription.delivery_method == ReportSubscription.DeliveryMethod.API:
        _deliver_api(subscription=subscription, payload=payload)
    else:
        raise ReportDeliveryError("Unsupported delivery method.")

    sent_at = timezone.now()
    subscription.last_sent_at = sent_at
    subscription.save(update_fields=["last_sent_at", "updated_at"])
    return {
        "status": "sent",
        "subscription_id": subscription.pk,
        "period_end": payload["period_end"],
        "sent_at": sent_at.isoformat(),
    }
