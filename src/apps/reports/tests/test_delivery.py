import json
from datetime import UTC, datetime
from urllib.error import HTTPError

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone

from apps.reports.delivery import ReportDeliveryError, deliver_report_subscription
from apps.reports.models import ReportSubscription
from apps.reports.selectors import get_due_report_subscriptions
from apps.reports.services import create_report_subscription
from apps.reports.tasks import (
    deliver_report_subscription_task,
    dispatch_due_report_subscriptions,
)

User = get_user_model()
AS_OF = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


@pytest.fixture
def staff_user():
    return User.objects.create_user(
        username="delivery-staff",
        email="delivery-staff@example.com",
        password="password123",
        is_staff=True,
    )


def _backdate_subscription(subscription, created_at):
    ReportSubscription.objects.filter(pk=subscription.pk).update(created_at=created_at)
    subscription.refresh_from_db()
    return subscription


@pytest.mark.django_db
def test_due_rules_respect_creation_time_last_sent_frequency_and_active_state(staff_user):
    weekly = create_report_subscription(
        actor=staff_user,
        frequency=ReportSubscription.Frequency.WEEKLY,
        delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
        email="weekly@example.com",
    )
    _backdate_subscription(weekly, datetime(2026, 9, 20, 12, 0, tzinfo=UTC))

    monthly = create_report_subscription(
        actor=staff_user,
        frequency=ReportSubscription.Frequency.MONTHLY,
        delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
        email="monthly@example.com",
    )
    _backdate_subscription(monthly, datetime(2026, 8, 20, 12, 0, tzinfo=UTC))
    ReportSubscription.objects.filter(pk=monthly.pk).update(
        last_sent_at=datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
    )

    too_new = create_report_subscription(
        actor=staff_user,
        frequency=ReportSubscription.Frequency.WEEKLY,
        delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
        email="new@example.com",
    )
    _backdate_subscription(too_new, datetime(2026, 9, 29, 12, 0, tzinfo=UTC))

    inactive = create_report_subscription(
        actor=staff_user,
        frequency=ReportSubscription.Frequency.WEEKLY,
        delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
        email="inactive@example.com",
        is_active=False,
    )
    _backdate_subscription(inactive, datetime(2026, 9, 20, 12, 0, tzinfo=UTC))

    due = get_due_report_subscriptions(as_of=AS_OF)
    assert [item.pk for item in due] == [weekly.pk]


@pytest.mark.django_db
def test_successful_email_delivery_updates_last_sent_and_same_period_is_idempotent(staff_user):
    subscription = create_report_subscription(
        actor=staff_user,
        frequency=ReportSubscription.Frequency.WEEKLY,
        delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
        email="ops@example.com",
    )
    _backdate_subscription(subscription, datetime(2026, 9, 20, 12, 0, tzinfo=UTC))

    first = deliver_report_subscription(subscription_id=subscription.pk, as_of=AS_OF)
    subscription.refresh_from_db()

    assert first["status"] == "sent"
    assert subscription.last_sent_at is not None
    assert len(mail.outbox) == 1
    assert "Weekly report" in mail.outbox[0].subject
    assert "Form submissions" in mail.outbox[0].body
    assert mail.outbox[0].alternatives[0].mimetype == "text/html"

    second = deliver_report_subscription(subscription_id=subscription.pk, as_of=AS_OF)
    assert second == {
        "status": "skipped",
        "reason": "not_due",
        "subscription_id": subscription.pk,
    }
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_failed_email_delivery_does_not_update_last_sent(monkeypatch, staff_user):
    subscription = create_report_subscription(
        actor=staff_user,
        frequency=ReportSubscription.Frequency.WEEKLY,
        delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
        email="ops@example.com",
    )
    _backdate_subscription(subscription, datetime(2026, 9, 20, 12, 0, tzinfo=UTC))

    def fail_send(*args, **kwargs):
        raise OSError("mail transport unavailable")

    monkeypatch.setattr("apps.reports.delivery.EmailMultiAlternatives.send", fail_send)
    with pytest.raises(ReportDeliveryError, match="Email delivery failed"):
        deliver_report_subscription(subscription_id=subscription.pk, as_of=AS_OF)

    subscription.refresh_from_db()
    assert subscription.last_sent_at is None


@pytest.mark.django_db
def test_successful_api_delivery_posts_shared_payload_with_timeout_and_idempotency_key(
    monkeypatch, staff_user
):
    subscription = create_report_subscription(
        actor=staff_user,
        frequency=ReportSubscription.Frequency.WEEKLY,
        delivery_method=ReportSubscription.DeliveryMethod.API,
        endpoint_url="https://example.com/report-hook",
    )
    _backdate_subscription(subscription, datetime(2026, 9, 20, 12, 0, tzinfo=UTC))
    captured = {}

    class Response:
        status = 202

        def getcode(self):
            return self.status

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("apps.reports.delivery.urlopen", fake_urlopen)
    result = deliver_report_subscription(subscription_id=subscription.pk, as_of=AS_OF)
    subscription.refresh_from_db()

    request = captured["request"]
    payload = json.loads(request.data.decode("utf-8"))
    assert result["status"] == "sent"
    assert captured["timeout"] == settings.REPORT_API_DELIVERY_TIMEOUT_SECONDS
    assert request.full_url == "https://example.com/report-hook"
    assert request.get_method() == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("Idempotency-key").startswith(
        f"dynamic-forms-report:{subscription.pk}:"
    )
    assert payload["schema_version"] == "1.0"
    assert payload["frequency"] == ReportSubscription.Frequency.WEEKLY
    assert "resume_token" not in str(payload).lower()
    assert subscription.last_sent_at is not None


@pytest.mark.django_db
@pytest.mark.parametrize("failure", ["http", "timeout"])
def test_api_delivery_failure_is_retryable_and_keeps_subscription_due(
    monkeypatch, staff_user, failure
):
    subscription = create_report_subscription(
        actor=staff_user,
        frequency=ReportSubscription.Frequency.WEEKLY,
        delivery_method=ReportSubscription.DeliveryMethod.API,
        endpoint_url="https://example.com/report-hook",
    )
    _backdate_subscription(subscription, datetime(2026, 9, 20, 12, 0, tzinfo=UTC))

    def fail_urlopen(request, timeout):
        if failure == "http":
            raise HTTPError(request.full_url, 503, "unavailable", {}, None)
        raise TimeoutError("timed out")

    monkeypatch.setattr("apps.reports.delivery.urlopen", fail_urlopen)
    with pytest.raises(ReportDeliveryError):
        deliver_report_subscription(subscription_id=subscription.pk, as_of=AS_OF)

    subscription.refresh_from_db()
    assert subscription.last_sent_at is None
    assert [item.pk for item in get_due_report_subscriptions(as_of=AS_OF)] == [subscription.pk]


@pytest.mark.django_db
def test_dispatcher_continues_when_one_delivery_cannot_be_scheduled(monkeypatch, staff_user):
    first = create_report_subscription(
        actor=staff_user,
        frequency=ReportSubscription.Frequency.WEEKLY,
        delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
        email="first@example.com",
    )
    second = create_report_subscription(
        actor=staff_user,
        frequency=ReportSubscription.Frequency.WEEKLY,
        delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
        email="second@example.com",
    )
    for subscription in (first, second):
        _backdate_subscription(subscription, datetime(2026, 9, 20, 12, 0, tzinfo=UTC))

    attempted = []

    def fake_delay(subscription_id, as_of_iso):
        attempted.append((subscription_id, as_of_iso))
        if subscription_id == second.pk:
            raise RuntimeError("broker rejected one message")

    monkeypatch.setattr(deliver_report_subscription_task, "delay", fake_delay)
    result = dispatch_due_report_subscriptions.run(AS_OF.isoformat())

    assert {item[0] for item in attempted} == {first.pk, second.pk}
    assert result == {"due": 2, "scheduled": 1, "failed_to_schedule": 1}


@pytest.mark.django_db
def test_celery_eager_delivery_executes_project_task(staff_user):
    subscription = create_report_subscription(
        actor=staff_user,
        frequency=ReportSubscription.Frequency.WEEKLY,
        delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
        email="eager@example.com",
    )
    _backdate_subscription(subscription, datetime(2026, 9, 20, 12, 0, tzinfo=UTC))

    result = deliver_report_subscription_task.delay(subscription.pk, AS_OF.isoformat())
    subscription.refresh_from_db()

    assert settings.CELERY_TASK_ALWAYS_EAGER is True
    assert result.successful()
    assert result.result["status"] == "sent"
    assert subscription.last_sent_at is not None


def test_beat_dispatcher_and_retry_bounds_are_registered():
    entry = settings.CELERY_BEAT_SCHEDULE["dispatch-due-periodic-reports-hourly"]
    assert entry["task"] == "apps.reports.tasks.dispatch_due_report_subscriptions"
    assert settings.REPORT_DELIVERY_MAX_RETRIES == 2
    assert deliver_report_subscription_task.max_retries == 2
