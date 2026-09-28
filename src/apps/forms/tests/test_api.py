import json

import pytest
from django.contrib.auth.hashers import check_password

from apps.accounts.models import User
from apps.core.models import Category
from apps.forms.models import Form
from apps.processes.models import Process, ProcessRun, ProcessStep

FORM_LIST_URL = "/api/v1/forms/"


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="form-api-other",
        email="form-api-other@example.com",
        password="test-password",
    )


def test_form_api_requires_authentication(client):
    response = client.get(FORM_LIST_URL)

    assert response.status_code == 403


@pytest.mark.django_db
def test_form_api_list_is_owner_scoped(client, user, other_user):
    Form.objects.create(owner=user, title="Visible")
    Form.objects.create(owner=other_user, title="Hidden")
    client.force_login(user)

    response = client.get(FORM_LIST_URL)

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["Visible"]


@pytest.mark.django_db
def test_form_api_creates_public_form_without_password_hash(client, user):
    client.force_login(user)

    response = client.post(
        FORM_LIST_URL,
        data=json.dumps({"title": "Public form"}),
        content_type="application/json",
    )

    assert response.status_code == 201
    payload = response.json()
    form = Form.objects.get(pk=payload["id"])

    assert form.access_password_hash is None
    assert "access_password_hash" not in payload


@pytest.mark.django_db
def test_form_api_creates_private_form_with_secure_hash(client, user):
    client.force_login(user)

    response = client.post(
        FORM_LIST_URL,
        data=json.dumps(
            {
                "title": "Private form",
                "visibility": Form.Visibility.PRIVATE,
                "access_password": "secret-pass",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    payload = response.json()
    form = Form.objects.get(pk=payload["id"])

    assert check_password("secret-pass", form.access_password_hash)
    assert "access_password_hash" not in payload
    assert "access_password" not in payload


@pytest.mark.django_db
def test_form_api_rejects_other_users_category(client, user, other_user):
    category = Category.objects.create(owner=other_user, name="Hidden")
    client.force_login(user)

    response = client.post(
        FORM_LIST_URL,
        data=json.dumps({"title": "Draft", "category_id": category.id}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "category" in response.json()["field_errors"]


@pytest.mark.django_db
def test_form_api_cross_user_detail_returns_404(client, user, other_user):
    form = Form.objects.create(owner=other_user, title="Hidden")
    client.force_login(user)

    response = client.get(f"{FORM_LIST_URL}{form.id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_form_api_patch_draft_and_reject_after_publish(client, user):
    form = Form.objects.create(owner=user, title="Draft")
    client.force_login(user)
    detail_url = f"{FORM_LIST_URL}{form.id}/"

    patch_response = client.patch(
        detail_url,
        data=json.dumps({"title": "Updated"}),
        content_type="application/json",
    )
    assert patch_response.status_code == 200

    publish_response = client.post(f"{detail_url}publish/")
    assert publish_response.status_code == 200

    blocked_response = client.patch(
        detail_url,
        data=json.dumps({"title": "Not allowed"}),
        content_type="application/json",
    )

    form.refresh_from_db()
    assert blocked_response.status_code == 400
    assert form.title == "Updated"
    assert form.status == Form.Status.PUBLISHED


@pytest.mark.django_db
def test_form_api_rejects_invalid_lifecycle_transitions(client, user):
    form = Form.objects.create(owner=user, title="Draft")
    client.force_login(user)
    detail_url = f"{FORM_LIST_URL}{form.id}/"

    assert client.post(f"{detail_url}close/").status_code == 400
    assert client.post(f"{detail_url}publish/").status_code == 200
    assert client.post(f"{detail_url}publish/").status_code == 400
    assert client.post(f"{detail_url}close/").status_code == 200
    assert client.post(f"{detail_url}close/").status_code == 400


@pytest.mark.django_db
def test_form_api_close_is_blocked_by_real_active_process_run(client, user):
    form = Form.objects.create(
        owner=user,
        title="Published form",
        status=Form.Status.PUBLISHED,
    )
    process = Process.objects.create(
        owner=user,
        title="Process",
        process_type=Process.ProcessType.LINEAR,
        status=Process.Status.PUBLISHED,
    )
    ProcessStep.objects.create(process=process, form=form, order=1)
    ProcessRun.objects.create(process=process, respondent=user)
    client.force_login(user)

    response = client.post(f"{FORM_LIST_URL}{form.id}/close/")

    form.refresh_from_db()
    assert response.status_code == 400
    assert form.status == Form.Status.PUBLISHED
    assert "status" in response.json()["field_errors"]


@pytest.mark.django_db
def test_form_api_only_deletes_drafts(client, user):
    draft = Form.objects.create(owner=user, title="Draft")
    published = Form.objects.create(
        owner=user,
        title="Published",
        status=Form.Status.PUBLISHED,
    )
    client.force_login(user)

    assert client.delete(f"{FORM_LIST_URL}{draft.id}/").status_code == 204
    assert client.delete(f"{FORM_LIST_URL}{published.id}/").status_code == 400
    assert not Form.objects.filter(pk=draft.pk).exists()
    assert Form.objects.filter(pk=published.pk).exists()


@pytest.mark.django_db
def test_openapi_declares_form_list_as_array_and_never_exposes_hash(client, user):
    client.force_login(user)

    response = client.get("/api/schema/", {"format": "json"})

    assert response.status_code == 200
    schema = response.json()
    response_schema = schema["paths"]["/api/v1/forms/"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]

    assert response_schema["type"] == "array"
    assert response_schema["items"]["$ref"] == "#/components/schemas/Form"
    assert "access_password_hash" not in schema["components"]["schemas"]["Form"]["properties"]
