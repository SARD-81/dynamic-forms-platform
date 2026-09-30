import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from apps.reports.models import ReportSubscription

User = get_user_model()


@pytest.fixture
def staff_user():
    return User.objects.create_user(
        username="http-report-staff",
        email="http-report-staff@example.com",
        password="password123",
        is_staff=True,
    )


@pytest.fixture
def ordinary_user():
    return User.objects.create_user(
        username="http-report-user",
        email="http-report-user@example.com",
        password="password123",
    )


@pytest.mark.django_db
def test_html_staff_can_create_list_update_deactivate_and_preview(staff_user):
    client = Client()
    client.force_login(staff_user)
    created = client.post(
        reverse("reports:create"),
        {
            "frequency": "WEEKLY",
            "delivery_method": "EMAIL",
            "email": "ops@example.com",
            "endpoint_url": "",
            "is_active": "on",
        },
    )
    assert created.status_code == 302
    subscription = ReportSubscription.objects.get()

    listing = client.get(reverse("reports:list"))
    assert listing.status_code == 200
    assert b"ops@example.com" in listing.content

    updated = client.post(
        reverse("reports:update", args=[subscription.pk]),
        {
            "frequency": "MONTHLY",
            "delivery_method": "API",
            "email": "",
            "endpoint_url": "https://example.com/report-hook",
            "is_active": "on",
        },
    )
    assert updated.status_code == 302
    subscription.refresh_from_db()
    assert subscription.delivery_method == "API"
    assert subscription.email is None

    preview = client.get(reverse("reports:preview"), {"frequency": "MONTHLY"})
    assert preview.status_code == 200
    assert b"Periodic report preview" in preview.content

    deactivated = client.post(reverse("reports:deactivate", args=[subscription.pk]))
    assert deactivated.status_code == 302
    subscription.refresh_from_db()
    assert subscription.is_active is False


@pytest.mark.django_db
def test_html_ordinary_user_is_denied(ordinary_user):
    client = Client()
    client.force_login(ordinary_user)
    assert client.get(reverse("reports:list")).status_code == 403
    assert client.get(reverse("reports:create")).status_code == 403
    assert client.get(reverse("reports:preview")).status_code == 403


@pytest.mark.django_db
def test_html_form_enforces_delivery_target_xor(staff_user):
    client = Client()
    client.force_login(staff_user)
    response = client.post(
        reverse("reports:create"),
        {
            "frequency": "WEEKLY",
            "delivery_method": "EMAIL",
            "email": "ops@example.com",
            "endpoint_url": "https://example.com/also-set",
            "is_active": "on",
        },
    )
    assert response.status_code == 200
    assert ReportSubscription.objects.count() == 0
    assert b"must be empty" in response.content


@pytest.mark.django_db
def test_rest_staff_crud_preview_and_normal_user_denied(staff_user, ordinary_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    created = client.post(
        "/api/v1/reports/subscriptions/",
        {
            "frequency": "WEEKLY",
            "delivery_method": "EMAIL",
            "email": "api@example.com",
            "is_active": True,
        },
        format="json",
    )
    assert created.status_code == 201
    subscription_id = created.data["id"]

    listing = client.get("/api/v1/reports/subscriptions/")
    assert listing.status_code == 200
    assert len(listing.data) == 1

    updated = client.put(
        f"/api/v1/reports/subscriptions/{subscription_id}/",
        {
            "frequency": "MONTHLY",
            "delivery_method": "API",
            "endpoint_url": "https://example.com/report-hook",
            "is_active": True,
        },
        format="json",
    )
    assert updated.status_code == 200
    assert updated.data["email"] is None

    preview = client.get("/api/v1/reports/preview/?frequency=WEEKLY")
    assert preview.status_code == 200
    assert preview.data["schema_version"] == "1.0"
    assert "resume_token" not in str(preview.data).lower()

    deactivated = client.post(f"/api/v1/reports/subscriptions/{subscription_id}/deactivate/")
    assert deactivated.status_code == 200
    assert deactivated.data["is_active"] is False

    client.force_authenticate(user=ordinary_user)
    assert client.get("/api/v1/reports/subscriptions/").status_code == 403
    assert client.get("/api/v1/reports/preview/?frequency=WEEKLY").status_code == 403


@pytest.mark.django_db
def test_rest_serializer_rejects_invalid_target_pair(staff_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    response = client.post(
        "/api/v1/reports/subscriptions/",
        {
            "frequency": "WEEKLY",
            "delivery_method": "API",
            "email": "wrong@example.com",
            "endpoint_url": "https://example.com/hook",
        },
        format="json",
    )
    assert response.status_code == 400
    assert ReportSubscription.objects.count() == 0
