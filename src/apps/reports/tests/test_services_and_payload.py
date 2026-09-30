from datetime import UTC, datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.forms.models import Form, FormSubmission
from apps.processes.models import Process, ProcessRun
from apps.reports.models import ReportSubscription
from apps.reports.selectors import get_due_report_subscriptions
from apps.reports.services import (
    create_report_subscription,
    deactivate_report_subscription,
    generate_periodic_report_payload,
    report_period_bounds,
    update_report_subscription,
)

User = get_user_model()


@pytest.fixture
def staff_user():
    return User.objects.create_user(
        username="report-staff",
        email="report-staff@example.com",
        password="password123",
        is_staff=True,
    )


@pytest.mark.django_db
def test_subscription_services_enforce_staff_and_target_xor(staff_user):
    ordinary = User.objects.create_user(
        username="report-ordinary",
        email="report-ordinary@example.com",
        password="password123",
    )
    with pytest.raises(PermissionDenied):
        create_report_subscription(
            actor=ordinary,
            frequency=ReportSubscription.Frequency.WEEKLY,
            delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            email="ops@example.com",
        )
    with pytest.raises(ValidationError):
        create_report_subscription(
            actor=staff_user,
            frequency=ReportSubscription.Frequency.WEEKLY,
            delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            email="ops@example.com",
            endpoint_url="https://example.com/hook",
        )

    email_subscription = create_report_subscription(
        actor=staff_user,
        frequency=ReportSubscription.Frequency.WEEKLY,
        delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
        email="ops@example.com",
    )
    api_subscription = create_report_subscription(
        actor=staff_user,
        frequency=ReportSubscription.Frequency.MONTHLY,
        delivery_method=ReportSubscription.DeliveryMethod.API,
        endpoint_url="https://example.com/reports",
    )
    assert email_subscription.endpoint_url is None
    assert api_subscription.email is None


@pytest.mark.django_db
def test_update_and_deactivate_never_touch_last_sent_at(staff_user):
    subscription = create_report_subscription(
        actor=staff_user,
        frequency=ReportSubscription.Frequency.WEEKLY,
        delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
        email="old@example.com",
    )
    sent_at = timezone.now() - timedelta(days=10)
    ReportSubscription.objects.filter(pk=subscription.pk).update(last_sent_at=sent_at)

    updated = update_report_subscription(
        actor=staff_user,
        subscription_id=subscription.pk,
        frequency=ReportSubscription.Frequency.MONTHLY,
        delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
        email="new@example.com",
        is_active=True,
    )
    assert updated.last_sent_at == sent_at
    deactivated = deactivate_report_subscription(actor=staff_user, subscription_id=subscription.pk)
    assert deactivated.is_active is False
    assert deactivated.last_sent_at == sent_at


def test_weekly_and_monthly_boundaries_are_completed_calendar_periods():
    as_of = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
    with timezone.override("UTC"):
        weekly_start, weekly_end = report_period_bounds(
            frequency=ReportSubscription.Frequency.WEEKLY,
            as_of=as_of,
        )
        monthly_start, monthly_end = report_period_bounds(
            frequency=ReportSubscription.Frequency.MONTHLY,
            as_of=as_of,
        )
    assert weekly_start == datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
    assert weekly_end == datetime(2026, 9, 28, 0, 0, tzinfo=UTC)
    assert monthly_start == datetime(2026, 8, 1, 0, 0, tzinfo=UTC)
    assert monthly_end == datetime(2026, 9, 1, 0, 0, tzinfo=UTC)


@pytest.mark.django_db
def test_payload_counts_period_activity_and_excludes_sensitive_data(staff_user):
    as_of = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
    with timezone.override("UTC"):
        form = Form.objects.create(owner=staff_user, title="Weekly form", view_count=11)
        Form.objects.filter(pk=form.pk).update(
            created_at=datetime(2026, 9, 23, 10, 0, tzinfo=UTC),
            status=Form.Status.PUBLISHED,
        )
        submission = FormSubmission.objects.create(form=form, respondent=staff_user)
        FormSubmission.objects.filter(pk=submission.pk).update(
            submitted_at=datetime(2026, 9, 24, 10, 0, tzinfo=UTC)
        )
        process = Process.objects.create(
            owner=staff_user,
            title="Weekly process",
            process_type=Process.ProcessType.LINEAR,
            view_count=7,
        )
        Process.objects.filter(pk=process.pk).update(
            created_at=datetime(2026, 9, 23, 11, 0, tzinfo=UTC),
            status=Process.Status.PUBLISHED,
        )
        run = ProcessRun.objects.create(process=process, respondent=staff_user)
        ProcessRun.objects.filter(pk=run.pk).update(
            started_at=datetime(2026, 9, 24, 11, 0, tzinfo=UTC),
            status=ProcessRun.Status.COMPLETED,
            completed_at=datetime(2026, 9, 25, 11, 0, tzinfo=UTC),
        )
        payload = generate_periodic_report_payload(
            frequency=ReportSubscription.Frequency.WEEKLY,
            as_of=as_of,
        )

    assert payload["activity"]["forms"]["created"] == 1
    assert payload["activity"]["forms"]["created_current_status"]["published"] == 1
    assert payload["activity"]["forms"]["submissions"] == 1
    assert payload["activity"]["processes"]["created"] == 1
    assert payload["activity"]["processes"]["runs_started"] == 1
    assert payload["activity"]["processes"]["runs_completed"] == 1
    assert payload["activity"]["cumulative_views"] == {"forms": 11, "processes": 7}
    serialized = str(payload).lower()
    assert "resume_token" not in serialized
    assert "password" not in serialized
    assert "report-staff@example.com" not in serialized


@pytest.mark.django_db
def test_empty_period_and_due_selector_excludes_inactive(staff_user):
    as_of = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
    with timezone.override("UTC"):
        payload = generate_periodic_report_payload(
            frequency=ReportSubscription.Frequency.WEEKLY,
            as_of=as_of,
        )
        active = create_report_subscription(
            actor=staff_user,
            frequency=ReportSubscription.Frequency.WEEKLY,
            delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            email="active@example.com",
        )
        create_report_subscription(
            actor=staff_user,
            frequency=ReportSubscription.Frequency.WEEKLY,
            delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            email="inactive@example.com",
            is_active=False,
        )
        due = get_due_report_subscriptions(as_of=as_of)

    assert payload["activity"]["forms"]["created"] == 0
    assert payload["activity"]["processes"]["runs_completed"] == 0
    assert [item.pk for item in due] == [active.pk]
