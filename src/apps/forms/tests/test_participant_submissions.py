from decimal import Decimal

import pytest
from django.contrib.auth.hashers import make_password
from django.urls import reverse

from apps.accounts.models import User
from apps.core.participant_access import grant_participant_access
from apps.forms.models import (
    Answer,
    AnswerOption,
    Form,
    FormSubmission,
    Question,
    QuestionOption,
)


@pytest.fixture
def submission_form(user):
    form = Form.objects.create(
        owner=user,
        title="Participant submission",
        description="Fill all required fields",
        status=Form.Status.PUBLISHED,
    )
    text = Question.objects.create(
        form=form,
        text="Name",
        question_type=Question.QuestionType.TEXT,
        order=1,
        is_required=True,
        max_length=20,
    )
    number = Question.objects.create(
        form=form,
        text="Age",
        question_type=Question.QuestionType.NUMBER,
        order=2,
        min_value=Decimal("0"),
        max_value=Decimal("120"),
    )
    select = Question.objects.create(
        form=form,
        text="Role",
        question_type=Question.QuestionType.SELECT,
        order=3,
        is_required=True,
    )
    option = QuestionOption.objects.create(question=select, label="Developer", order=1)
    optional_select = Question.objects.create(
        form=form,
        text="Optional role",
        question_type=Question.QuestionType.SELECT,
        order=4,
        is_required=False,
    )
    optional_option = QuestionOption.objects.create(
        question=optional_select,
        label="Optional developer",
        order=1,
    )
    checkbox = Question.objects.create(
        form=form,
        text="Tools",
        question_type=Question.QuestionType.CHECKBOX,
        order=5,
    )
    check = QuestionOption.objects.create(question=checkbox, label="Git", order=1)
    return {
        "form": form,
        "text": text,
        "number": number,
        "select": select,
        "option": option,
        "optional_select": optional_select,
        "optional_option": optional_option,
        "checkbox": checkbox,
        "check": check,
    }


@pytest.fixture
def private_submission_form(user):
    form = Form.objects.create(
        owner=user,
        title="Private submission",
        visibility=Form.Visibility.PRIVATE,
        access_password_hash=make_password("secret"),
        status=Form.Status.PUBLISHED,
    )
    text = Question.objects.create(
        form=form,
        text="Secret answer",
        question_type=Question.QuestionType.TEXT,
        order=1,
        is_required=True,
    )
    return form, text


@pytest.mark.django_db
def test_html_form_renders_real_dynamic_inputs(client, submission_form):
    response = client.get(
        reverse("forms_participant:detail", args=[submission_form["form"].public_id])
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert f'name="q_{submission_form["text"].id}"' in content
    assert f'name="q_{submission_form["number"].id}"' in content
    assert f'name="q_{submission_form["select"].id}"' in content
    assert f'name="q_{submission_form["optional_select"].id}"' in content
    assert f'name="q_{submission_form["checkbox"].id}"' in content
    assert "Submit form" in content


@pytest.mark.django_db
def test_html_anonymous_submission_creates_receipt_and_answers(client, submission_form):
    response = client.post(
        reverse("forms_participant:submit", args=[submission_form["form"].public_id]),
        {
            f"q_{submission_form['text'].id}": "Anonymous",
            f"q_{submission_form['number'].id}": "25",
            f"q_{submission_form['select'].id}": str(submission_form["option"].id),
            f"q_{submission_form['checkbox'].id}": [str(submission_form["check"].id)],
        },
    )

    assert response.status_code == 200
    assert "Submission received" in response.content.decode()
    submission = FormSubmission.objects.get(form=submission_form["form"])
    assert submission.respondent is None
    assert submission.answers.count() == 4


@pytest.mark.django_db
def test_html_validation_errors_are_question_scoped_and_preserve_values(
    client,
    submission_form,
):
    response = client.post(
        reverse("forms_participant:submit", args=[submission_form["form"].public_id]),
        {
            f"q_{submission_form['text'].id}": "",
            f"q_{submission_form['select'].id}": "",
        },
    )
    content = response.content.decode()

    assert response.status_code == 400
    assert "This question is required." in content
    assert not FormSubmission.objects.filter(form=submission_form["form"]).exists()


@pytest.mark.django_db
def test_html_optional_select_placeholder_is_treated_as_omitted(client, submission_form):
    response = client.post(
        reverse("forms_participant:submit", args=[submission_form["form"].public_id]),
        {
            f"q_{submission_form['text'].id}": "Optional select omitted",
            f"q_{submission_form['select'].id}": str(submission_form["option"].id),
            f"q_{submission_form['optional_select'].id}": "",
        },
    )

    assert response.status_code == 200
    submission = FormSubmission.objects.get(form=submission_form["form"])
    assert not submission.answers.filter(
        question=submission_form["optional_select"]
    ).exists()


@pytest.mark.django_db
def test_html_required_select_placeholder_returns_required_error(client, submission_form):
    response = client.post(
        reverse("forms_participant:submit", args=[submission_form["form"].public_id]),
        {
            f"q_{submission_form['text'].id}": "Required select missing",
            f"q_{submission_form['select'].id}": "",
        },
    )

    assert response.status_code == 400
    content = response.content.decode()
    assert "This question is required." in content
    assert "A positive integer ID is required." not in content
    assert not FormSubmission.objects.filter(form=submission_form["form"]).exists()
    assert not Answer.objects.filter(question__form=submission_form["form"]).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("question_key", ["text", "number", "select"])
def test_html_duplicate_values_for_single_value_question_are_rejected(
    client,
    submission_form,
    question_key,
):
    field_name = f"q_{submission_form[question_key].id}"
    post_data = {
        f"q_{submission_form['text'].id}": "Valid text",
        f"q_{submission_form['number'].id}": "30",
        f"q_{submission_form['select'].id}": str(submission_form["option"].id),
    }

    if question_key == "select":
        post_data[field_name] = [
            str(submission_form["option"].id),
            str(submission_form["option"].id),
        ]
    elif question_key == "number":
        post_data[field_name] = ["30", "31"]
    else:
        post_data[field_name] = ["first", "second"]

    response = client.post(
        reverse("forms_participant:submit", args=[submission_form["form"].public_id]),
        post_data,
    )

    assert response.status_code == 400
    assert (
        "Multiple values for a single-value question are not allowed."
        in response.content.decode()
    )
    assert not FormSubmission.objects.filter(form=submission_form["form"]).exists()
    assert not Answer.objects.filter(question__form=submission_form["form"]).exists()
    assert not AnswerOption.objects.filter(
        answer__question__form=submission_form["form"]
    ).exists()


@pytest.mark.django_db
def test_html_forged_cross_form_question_is_rejected(client, user, submission_form):
    foreign_form = Form.objects.create(
        owner=user,
        title="Foreign",
        status=Form.Status.PUBLISHED,
    )
    foreign_question = Question.objects.create(
        form=foreign_form,
        text="Foreign",
        question_type=Question.QuestionType.TEXT,
        order=1,
    )

    response = client.post(
        reverse("forms_participant:submit", args=[submission_form["form"].public_id]),
        {
            f"q_{submission_form['text'].id}": "Valid",
            f"q_{submission_form['select'].id}": str(submission_form["option"].id),
            f"q_{foreign_question.id}": "Forged",
        },
    )

    assert response.status_code == 400
    assert "Invalid question ID for this form." in response.content.decode()
    assert not FormSubmission.objects.filter(form=submission_form["form"]).exists()


@pytest.mark.django_db
def test_rest_authenticated_submission_records_respondent(
    client,
    user,
    submission_form,
):
    respondent = User.objects.create_user(
        username="api-respondent",
        email="api-respondent@example.com",
        password="test-password",
    )
    client.force_login(respondent)
    url = f"/api/v1/public/forms/{submission_form['form'].public_id}/submissions/"

    response = client.post(
        url,
        data={
            "answers": [
                {
                    "question_id": submission_form["text"].id,
                    "text_value": "Authenticated",
                },
                {
                    "question_id": submission_form["select"].id,
                    "option_ids": [submission_form["option"].id],
                },
            ]
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json()) == {"public_id", "submitted_at"}
    submission = FormSubmission.objects.get(public_id=response.json()["public_id"])
    assert submission.respondent == respondent
    assert submission.form == submission_form["form"]


@pytest.mark.django_db
def test_rest_returns_question_level_validation_errors(client, submission_form):
    url = f"/api/v1/public/forms/{submission_form['form'].public_id}/submissions/"

    response = client.post(
        url,
        data={
            "answers": [
                {
                    "question_id": submission_form["text"].id,
                    "text_value": "",
                },
                {
                    "question_id": submission_form["select"].id,
                    "option_ids": [],
                },
            ]
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "FORM_SUBMISSION_VALIDATION_ERROR"
    assert f"question_{submission_form['text'].id}" in payload["field_errors"]
    assert f"question_{submission_form['select'].id}" in payload["field_errors"]


@pytest.mark.django_db
def test_private_submission_requires_existing_participant_grant(
    client,
    private_submission_form,
):
    form, question = private_submission_form
    html_url = reverse("forms_participant:submit", args=[form.public_id])
    api_url = f"/api/v1/public/forms/{form.public_id}/submissions/"

    assert client.post(html_url, {f"q_{question.id}": "No grant"}).status_code == 403
    assert (
        client.post(
            api_url,
            data={"answers": [{"question_id": question.id, "text_value": "No grant"}]},
            content_type="application/json",
        ).status_code
        == 403
    )

    session = client.session
    grant_participant_access(
        session=session,
        resource_type="form",
        public_id=form.public_id,
    )
    session.save()

    allowed = client.post(
        api_url,
        data={"answers": [{"question_id": question.id, "text_value": "Granted"}]},
        content_type="application/json",
    )
    assert allowed.status_code == 201


@pytest.mark.django_db
@pytest.mark.parametrize("status", [Form.Status.DRAFT, Form.Status.CLOSED])
def test_non_published_form_submission_routes_are_not_exposed(client, user, status):
    form = Form.objects.create(owner=user, title="Unavailable", status=status)

    html = client.post(reverse("forms_participant:submit", args=[form.public_id]), {})
    api = client.post(
        f"/api/v1/public/forms/{form.public_id}/submissions/",
        data={"answers": []},
        content_type="application/json",
    )

    assert html.status_code == 404
    assert api.status_code == 404


@pytest.mark.django_db
def test_submission_receipt_does_not_expose_existing_submission_data(
    client,
    submission_form,
):
    other = FormSubmission.objects.create(form=submission_form["form"])
    Answer.objects.create(
        submission=other,
        question=submission_form["text"],
        text_value="Private previous response",
    )

    response = client.post(
        f"/api/v1/public/forms/{submission_form['form'].public_id}/submissions/",
        data={
            "answers": [
                {
                    "question_id": submission_form["text"].id,
                    "text_value": "New response",
                },
                {
                    "question_id": submission_form["select"].id,
                    "option_ids": [submission_form["option"].id],
                },
            ]
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert str(other.public_id) not in response.content.decode()
    assert "Private previous response" not in response.content.decode()


@pytest.mark.django_db
def test_submission_openapi_documents_public_submission_endpoint(client):
    response = client.get("/api/schema/", {"format": "json"})

    assert response.status_code == 200
    schema = response.json()
    operation = schema["paths"]["/api/v1/public/forms/{public_id}/submissions/"]["post"]
    assert "201" in operation["responses"]
