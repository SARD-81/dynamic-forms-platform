import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.forms.models import Answer, Form, FormSubmission, Question


@pytest.fixture
def report_form(user):
    form = Form.objects.create(
        owner=user,
        title="HTML report",
        status=Form.Status.PUBLISHED,
        view_count=4,
    )
    question = Question.objects.create(
        form=form,
        text="Feedback",
        question_type=Question.QuestionType.TEXT,
        order=1,
    )
    return form, question


@pytest.mark.django_db
def test_html_report_requires_login(client, report_form):
    form, _ = report_form

    response = client.get(reverse("forms:report", args=[form.id]))

    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


@pytest.mark.django_db
def test_html_report_is_owner_scoped(client, user, other_user, report_form):
    form, _ = report_form
    client.force_login(other_user)

    response = client.get(reverse("forms:report", args=[form.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_html_report_dashboard_shows_totals_and_question_semantics(client, user, report_form):
    form, question = report_form
    FormSubmission.objects.create(form=form)
    client.force_login(user)

    response = client.get(reverse("forms:report", args=[form.id]))
    content = response.content.decode()

    assert response.status_code == 200
    assert "HTML report" in content
    assert "Submitted responses" in content
    assert "Question analytics" in content
    assert "Feedback" in content
    assert "4" in content
    assert str(question.order) in content


@pytest.mark.django_db
def test_form_management_detail_links_to_owner_report(client, user, report_form):
    form, _ = report_form
    client.force_login(user)

    response = client.get(reverse("forms:detail", args=[form.id]))

    assert response.status_code == 200
    assert reverse("forms:report", args=[form.id]) in response.content.decode()


@pytest.mark.django_db
def test_html_response_browser_is_paginated(client, user, report_form):
    form, _ = report_form
    for _ in range(25):
        FormSubmission.objects.create(form=form)
    client.force_login(user)

    first = client.get(reverse("forms:report_responses", args=[form.id]))
    second = client.get(reverse("forms:report_responses", args=[form.id]), {"page": 2})

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(first.context["response_items"]) == 20
    assert len(second.context["response_items"]) == 5
    assert first.context["page_obj"].paginator.count == 25


@pytest.mark.django_db
def test_html_response_detail_shows_answer_but_not_user_identity(
    client,
    user,
    report_form,
):
    form, question = report_form
    respondent = User.objects.create_user(
        username="private-report-user",
        email="private-report-user@example.com",
        password="test-password",
    )
    submission = FormSubmission.objects.create(form=form, respondent=respondent)
    Answer.objects.create(
        submission=submission,
        question=question,
        text_value="Visible answer",
    )
    client.force_login(user)

    response = client.get(
        reverse(
            "forms:report_response_detail",
            args=[form.id, submission.public_id],
        )
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert "Visible answer" in content
    assert "Authenticated" in content
    assert "private-report-user" not in content
    assert "private-report-user@example.com" not in content


@pytest.mark.django_db
def test_html_response_detail_rejects_submission_from_another_form(
    client,
    user,
    report_form,
):
    form, _ = report_form
    foreign = Form.objects.create(
        owner=user,
        title="Foreign form",
        status=Form.Status.PUBLISHED,
    )
    submission = FormSubmission.objects.create(form=foreign)
    client.force_login(user)

    response = client.get(
        reverse(
            "forms:report_response_detail",
            args=[form.id, submission.public_id],
        )
    )

    assert response.status_code == 404
