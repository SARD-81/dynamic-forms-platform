from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.forms.models import (
    Answer,
    AnswerOption,
    Form,
    FormSubmission,
    Question,
    QuestionOption,
)
from apps.forms.submission_services import submit_form


@pytest.fixture
def respondent(db):
    return User.objects.create_user(
        username="submission-respondent",
        email="submission-respondent@example.com",
        password="test-password",
    )


@pytest.fixture
def submission_schema(user):
    form = Form.objects.create(
        owner=user,
        title="Submission schema",
        status=Form.Status.PUBLISHED,
    )
    text = Question.objects.create(
        form=form,
        text="Name",
        question_type=Question.QuestionType.TEXT,
        order=1,
        is_required=True,
        max_length=10,
    )
    number = Question.objects.create(
        form=form,
        text="Score",
        question_type=Question.QuestionType.NUMBER,
        order=2,
        is_required=True,
        min_value=Decimal("1"),
        max_value=Decimal("10"),
    )
    select = Question.objects.create(
        form=form,
        text="Pick one",
        question_type=Question.QuestionType.SELECT,
        order=3,
        is_required=True,
    )
    select_one = QuestionOption.objects.create(question=select, label="One", order=1)
    select_two = QuestionOption.objects.create(question=select, label="Two", order=2)
    checkbox = Question.objects.create(
        form=form,
        text="Pick many",
        question_type=Question.QuestionType.CHECKBOX,
        order=4,
        is_required=False,
    )
    check_one = QuestionOption.objects.create(question=checkbox, label="A", order=1)
    check_two = QuestionOption.objects.create(question=checkbox, label="B", order=2)
    return {
        "form": form,
        "text": text,
        "number": number,
        "select": select,
        "select_one": select_one,
        "select_two": select_two,
        "checkbox": checkbox,
        "check_one": check_one,
        "check_two": check_two,
    }


def valid_answers(schema):
    return [
        {"question_id": schema["text"].id, "text_value": "Alice"},
        {"question_id": schema["number"].id, "number_value": "7.5"},
        {"question_id": schema["select"].id, "option_ids": [schema["select_two"].id]},
        {
            "question_id": schema["checkbox"].id,
            "option_ids": [schema["check_one"].id, schema["check_two"].id],
        },
    ]


@pytest.mark.django_db
def test_submit_form_persists_all_frozen_answer_types_atomically(
    submission_schema,
    respondent,
):
    submission = submit_form(
        form=submission_schema["form"],
        answers=valid_answers(submission_schema),
        respondent=respondent,
    )

    assert submission.respondent == respondent
    answers = {
        answer.question_id: answer
        for answer in submission.answers.prefetch_related("selected_options__option")
    }
    assert answers[submission_schema["text"].id].text_value == "Alice"
    assert answers[submission_schema["number"].id].number_value == Decimal("7.500000")
    assert answers[submission_schema["select"].id].text_value is None
    assert list(
        answers[submission_schema["select"].id].selected_options.values_list(
            "option_id",
            flat=True,
        )
    ) == [submission_schema["select_two"].id]
    assert set(
        answers[submission_schema["checkbox"].id].selected_options.values_list(
            "option_id",
            flat=True,
        )
    ) == {submission_schema["check_one"].id, submission_schema["check_two"].id}


@pytest.mark.django_db
def test_anonymous_submission_keeps_respondent_null(submission_schema):
    submission = submit_form(
        form=submission_schema["form"],
        answers=valid_answers(submission_schema),
        respondent=None,
    )

    assert submission.respondent is None


@pytest.mark.django_db
@pytest.mark.parametrize("status", [Form.Status.DRAFT, Form.Status.CLOSED])
def test_submission_service_rejects_non_published_forms(user, status):
    form = Form.objects.create(owner=user, title="Unavailable", status=status)

    with pytest.raises(ValidationError) as exc_info:
        submit_form(form=form, answers=[])

    assert "form" in exc_info.value.message_dict
    assert not FormSubmission.objects.filter(form=form).exists()


@pytest.mark.django_db
def test_submission_rejects_missing_required_question(submission_schema):
    answers = valid_answers(submission_schema)
    answers = [
        answer
        for answer in answers
        if answer["question_id"] != submission_schema["text"].id
    ]

    with pytest.raises(ValidationError) as exc_info:
        submit_form(form=submission_schema["form"], answers=answers)

    assert f"question_{submission_schema['text'].id}" in exc_info.value.message_dict
    assert not FormSubmission.objects.filter(form=submission_schema["form"]).exists()


@pytest.mark.django_db
def test_optional_checkbox_can_be_omitted(submission_schema):
    answers = [
        answer
        for answer in valid_answers(submission_schema)
        if answer["question_id"] != submission_schema["checkbox"].id
    ]

    submission = submit_form(form=submission_schema["form"], answers=answers)

    assert not submission.answers.filter(question=submission_schema["checkbox"]).exists()


@pytest.mark.django_db
def test_text_validation_rejects_length_and_incompatible_payload(submission_schema):
    answers = valid_answers(submission_schema)
    answers[0] = {
        "question_id": submission_schema["text"].id,
        "text_value": "x" * 11,
        "number_value": "1",
    }

    with pytest.raises(ValidationError) as exc_info:
        submit_form(form=submission_schema["form"], answers=answers)

    errors = exc_info.value.message_dict[f"question_{submission_schema['text'].id}"]
    assert any("only text_value" in message for message in errors)


@pytest.mark.django_db
@pytest.mark.parametrize("value", ["NaN", "Infinity", "abc", "0", "11"])
def test_number_validation_rejects_invalid_or_out_of_range_values(
    submission_schema,
    value,
):
    answers = valid_answers(submission_schema)
    answers[1] = {
        "question_id": submission_schema["number"].id,
        "number_value": value,
    }

    with pytest.raises(ValidationError) as exc_info:
        submit_form(form=submission_schema["form"], answers=answers)

    assert f"question_{submission_schema['number'].id}" in exc_info.value.message_dict


@pytest.mark.django_db
def test_number_validation_rejects_database_precision_overflow(submission_schema):
    answers = valid_answers(submission_schema)
    answers[1] = {
        "question_id": submission_schema["number"].id,
        "number_value": "1.1234567",
    }

    with pytest.raises(ValidationError) as exc_info:
        submit_form(form=submission_schema["form"], answers=answers)

    assert f"question_{submission_schema['number'].id}" in exc_info.value.message_dict


@pytest.mark.django_db
def test_select_requires_exactly_one_option(submission_schema):
    answers = valid_answers(submission_schema)
    answers[2] = {
        "question_id": submission_schema["select"].id,
        "option_ids": [
            submission_schema["select_one"].id,
            submission_schema["select_two"].id,
        ],
    }

    with pytest.raises(ValidationError) as exc_info:
        submit_form(form=submission_schema["form"], answers=answers)

    errors = exc_info.value.message_dict[f"question_{submission_schema['select'].id}"]
    assert any("exactly one" in message for message in errors)


@pytest.mark.django_db
def test_checkbox_rejects_duplicate_option_ids(submission_schema):
    answers = valid_answers(submission_schema)
    answers[3] = {
        "question_id": submission_schema["checkbox"].id,
        "option_ids": [
            submission_schema["check_one"].id,
            submission_schema["check_one"].id,
        ],
    }

    with pytest.raises(ValidationError) as exc_info:
        submit_form(form=submission_schema["form"], answers=answers)

    errors = exc_info.value.message_dict[f"question_{submission_schema['checkbox'].id}"]
    assert any("Duplicate option IDs" in message for message in errors)


@pytest.mark.django_db
def test_submission_rejects_duplicate_answers_for_question(submission_schema):
    answers = valid_answers(submission_schema)
    answers.append(
        {
            "question_id": submission_schema["text"].id,
            "text_value": "Second",
        }
    )

    with pytest.raises(ValidationError) as exc_info:
        submit_form(form=submission_schema["form"], answers=answers)

    errors = exc_info.value.message_dict[f"question_{submission_schema['text'].id}"]
    assert any("Duplicate answers" in message for message in errors)


@pytest.mark.django_db
def test_service_only_invariant_rejects_question_from_another_form(
    user,
    submission_schema,
):
    foreign_form = Form.objects.create(
        owner=user,
        title="Foreign",
        status=Form.Status.PUBLISHED,
    )
    foreign_question = Question.objects.create(
        form=foreign_form,
        text="Foreign question",
        question_type=Question.QuestionType.TEXT,
        order=1,
    )
    answers = valid_answers(submission_schema)
    answers.append(
        {
            "question_id": foreign_question.id,
            "text_value": "Should not persist",
        }
    )

    with pytest.raises(ValidationError) as exc_info:
        submit_form(form=submission_schema["form"], answers=answers)

    errors = exc_info.value.message_dict[f"question_{foreign_question.id}"]
    assert any("does not belong to this form" in message for message in errors)
    assert not FormSubmission.objects.filter(form=submission_schema["form"]).exists()


@pytest.mark.django_db
def test_service_only_invariant_rejects_option_from_another_question(
    submission_schema,
):
    answers = valid_answers(submission_schema)
    answers[2] = {
        "question_id": submission_schema["select"].id,
        "option_ids": [submission_schema["check_one"].id],
    }

    with pytest.raises(ValidationError) as exc_info:
        submit_form(form=submission_schema["form"], answers=answers)

    errors = exc_info.value.message_dict[f"question_{submission_schema['select'].id}"]
    assert any("does not belong to this question" in message for message in errors)
    assert not FormSubmission.objects.filter(form=submission_schema["form"]).exists()


@pytest.mark.django_db
def test_submission_rejects_unknown_question_and_option_ids(submission_schema):
    answers = valid_answers(submission_schema)
    answers.append({"question_id": 999999, "text_value": "Unknown"})
    answers[2] = {
        "question_id": submission_schema["select"].id,
        "option_ids": [999999],
    }

    with pytest.raises(ValidationError) as exc_info:
        submit_form(form=submission_schema["form"], answers=answers)

    errors = exc_info.value.message_dict
    assert "Unknown question ID." in errors["question_999999"]
    assert "Unknown option ID." in errors[f"question_{submission_schema['select'].id}"]


@pytest.mark.django_db
def test_persistence_failure_rolls_back_submission_and_answers(submission_schema):
    answers = valid_answers(submission_schema)

    with patch(
        "apps.forms.submission_services.AnswerOption.objects.bulk_create",
        side_effect=RuntimeError("simulated persistence failure"),
    ):
        with pytest.raises(RuntimeError):
            submit_form(form=submission_schema["form"], answers=answers)

    assert not FormSubmission.objects.filter(form=submission_schema["form"]).exists()
    assert not Answer.objects.filter(question__form=submission_schema["form"]).exists()
    assert not AnswerOption.objects.filter(
        answer__question__form=submission_schema["form"]
    ).exists()
