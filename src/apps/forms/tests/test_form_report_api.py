import pytest

from apps.accounts.models import User
from apps.forms.models import Answer, Form, FormSubmission, Question


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="report-other",
        email="report-other@example.com",
        password="test-password",
    )


@pytest.fixture
def api_report_form(user):
    form = Form.objects.create(
        owner=user,
        title="API report",
        status=Form.Status.PUBLISHED,
        view_count=12,
    )
    question = Question.objects.create(
        form=form,
        text="API feedback",
        question_type=Question.QuestionType.TEXT,
        order=1,
    )
    return form, question


@pytest.mark.django_db
def test_rest_report_requires_authentication(client, api_report_form):
    form, _ = api_report_form

    response = client.get(f"/api/v1/forms/{form.id}/report/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_rest_report_summary_is_owner_scoped(client, other_user, api_report_form):
    form, _ = api_report_form
    client.force_login(other_user)

    response = client.get(f"/api/v1/forms/{form.id}/report/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_rest_report_summary_exposes_required_metrics(client, user, api_report_form):
    form, _ = api_report_form
    FormSubmission.objects.create(form=form)
    client.force_login(user)

    response = client.get(f"/api/v1/forms/{form.id}/report/")
    payload = response.json()

    assert response.status_code == 200
    assert payload["title"] == "API report"
    assert payload["view_count"] == 12
    assert payload["total_submissions"] == 1
    assert payload["questions"][0]["answered_count"] == 0
    assert payload["questions"][0]["unanswered_count"] == 1


@pytest.mark.django_db
def test_rest_response_list_is_paginated_and_privacy_safe(client, user, api_report_form):
    form, _ = api_report_form
    respondent = User.objects.create_user(
        username="hidden-api-user",
        email="hidden-api-user@example.com",
        password="test-password",
    )
    for index in range(25):
        FormSubmission.objects.create(
            form=form,
            respondent=respondent if index == 0 else None,
        )
    client.force_login(user)

    first = client.get(f"/api/v1/forms/{form.id}/responses/")
    second = client.get(f"/api/v1/forms/{form.id}/responses/", {"page": 2})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["count"] == 25
    assert len(first.json()["results"]) == 20
    assert len(second.json()["results"]) == 5
    combined = str(first.json()) + str(second.json())
    assert "hidden-api-user" not in combined
    assert "hidden-api-user@example.com" not in combined
    assert {item["respondent_type"] for item in first.json()["results"]} <= {
        "anonymous",
        "authenticated",
    }


@pytest.mark.django_db
def test_rest_response_list_respects_bounded_page_size(client, user, api_report_form):
    form, _ = api_report_form
    for _ in range(105):
        FormSubmission.objects.create(form=form)
    client.force_login(user)

    response = client.get(
        f"/api/v1/forms/{form.id}/responses/",
        {"page_size": 500},
    )

    assert response.status_code == 200
    assert len(response.json()["results"]) == 100


@pytest.mark.django_db
def test_rest_response_detail_returns_values_without_identity(client, user, api_report_form):
    form, question = api_report_form
    respondent = User.objects.create_user(
        username="secret-identity",
        email="secret-identity@example.com",
        password="test-password",
    )
    submission = FormSubmission.objects.create(form=form, respondent=respondent)
    Answer.objects.create(
        submission=submission,
        question=question,
        text_value="REST visible value",
    )
    client.force_login(user)

    response = client.get(f"/api/v1/forms/{form.id}/responses/{submission.public_id}/")
    payload = response.json()

    assert response.status_code == 200
    assert payload["respondent_type"] == "authenticated"
    assert payload["answers"][0]["text_value"] == "REST visible value"
    serialized = str(payload)
    assert "secret-identity" not in serialized
    assert "secret-identity@example.com" not in serialized


@pytest.mark.django_db
def test_rest_response_detail_is_form_and_owner_scoped(
    client,
    user,
    other_user,
    api_report_form,
):
    form, _ = api_report_form
    foreign_form = Form.objects.create(
        owner=other_user,
        title="Foreign report",
        status=Form.Status.PUBLISHED,
    )
    foreign_submission = FormSubmission.objects.create(form=foreign_form)
    client.force_login(user)

    response = client.get(f"/api/v1/forms/{form.id}/responses/{foreign_submission.public_id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_form_report_openapi_paths_are_documented(client, user):
    client.force_login(user)

    response = client.get("/api/schema/", {"format": "json"})
    schema = response.json()

    assert response.status_code == 200
    assert "/api/v1/forms/{form_id}/report/" in schema["paths"]
    assert "/api/v1/forms/{form_id}/responses/" in schema["paths"]
    assert "/api/v1/forms/{form_id}/responses/{submission_public_id}/" in schema["paths"]
