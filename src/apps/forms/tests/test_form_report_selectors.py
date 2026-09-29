from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.cache import cache

from apps.accounts.models import User
from apps.forms.models import Form, FormSubmission, Question, QuestionOption
from apps.forms.report_cache import form_report_cache_key
from apps.forms.report_selectors import (
    get_form_report_submission_detail,
    get_form_report_summary,
)
from apps.forms.submission_services import submit_form


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="report-other",
        email="report-other@example.com",
        password="test-password",
    )


@pytest.fixture
def report_respondent(db):
    return User.objects.create_user(
        username="report-respondent",
        email="report-respondent@example.com",
        password="test-password",
    )


@pytest.fixture
def report_schema(user):
    form = Form.objects.create(
        owner=user,
        title="Report survey",
        status=Form.Status.PUBLISHED,
        view_count=9,
    )
    text = Question.objects.create(
        form=form,
        text="Comment",
        question_type=Question.QuestionType.TEXT,
        order=1,
        is_required=False,
    )
    number = Question.objects.create(
        form=form,
        text="Score",
        question_type=Question.QuestionType.NUMBER,
        order=2,
        is_required=True,
    )
    select = Question.objects.create(
        form=form,
        text="Role",
        question_type=Question.QuestionType.SELECT,
        order=3,
        is_required=False,
    )
    select_a = QuestionOption.objects.create(question=select, label="A", order=1)
    select_b = QuestionOption.objects.create(question=select, label="B", order=2)
    checkbox = Question.objects.create(
        form=form,
        text="Tools",
        question_type=Question.QuestionType.CHECKBOX,
        order=4,
        is_required=False,
    )
    check_a = QuestionOption.objects.create(question=checkbox, label="X", order=1)
    check_b = QuestionOption.objects.create(question=checkbox, label="Y", order=2)
    return {
        "form": form,
        "text": text,
        "number": number,
        "select": select,
        "select_a": select_a,
        "select_b": select_b,
        "checkbox": checkbox,
        "check_a": check_a,
        "check_b": check_b,
    }


def _submit(schema, *, text=None, number, select=None, checkbox=None, respondent=None):
    answers = [{"question_id": schema["number"].id, "number_value": str(number)}]
    if text is not None:
        answers.append({"question_id": schema["text"].id, "text_value": text})
    if select is not None:
        answers.append({"question_id": schema["select"].id, "option_ids": [select.id]})
    if checkbox is not None:
        answers.append(
            {
                "question_id": schema["checkbox"].id,
                "option_ids": [option.id for option in checkbox],
            }
        )
    return submit_form(
        form=schema["form"],
        answers=answers,
        respondent=respondent,
    )


@pytest.mark.django_db
def test_zero_submission_report_has_live_view_count_and_zero_question_denominators(
    user,
    report_schema,
):
    cache.clear()

    report = get_form_report_summary(owner=user, form_id=report_schema["form"].id)

    assert report["view_count"] == 9
    assert report["total_submissions"] == 0
    assert report["recent_activity"] == []
    assert report["timeline"] == []
    assert len(report["questions"]) == 4
    for question in report["questions"]:
        assert question["answered_count"] == 0
        assert question["unanswered_count"] == 0
    assert all(
        option["percentage"] == Decimal("0.00")
        for question in report["questions"]
        for option in question["options"]
    )


@pytest.mark.django_db
def test_form_report_aggregates_number_select_checkbox_and_optional_answers(
    user,
    report_respondent,
    report_schema,
):
    cache.clear()
    _submit(
        report_schema,
        text="first",
        number=10,
        select=report_schema["select_a"],
        checkbox=[report_schema["check_a"], report_schema["check_b"]],
        respondent=report_respondent,
    )
    _submit(
        report_schema,
        number=20,
        select=report_schema["select_b"],
        checkbox=[report_schema["check_a"]],
    )
    _submit(
        report_schema,
        text="third",
        number=30,
    )

    report = get_form_report_summary(owner=user, form_id=report_schema["form"].id)
    by_id = {question["id"]: question for question in report["questions"]}

    assert report["total_submissions"] == 3
    assert report["view_count"] == 9
    assert len(report["recent_activity"]) == 3
    assert {item["respondent_type"] for item in report["recent_activity"]} == {
        "anonymous",
        "authenticated",
    }

    text = by_id[report_schema["text"].id]
    assert text["answered_count"] == 2
    assert text["unanswered_count"] == 1
    assert text["number_average"] is None

    number = by_id[report_schema["number"].id]
    assert number["answered_count"] == 3
    assert number["unanswered_count"] == 0
    assert number["number_min"] == Decimal("10.000000")
    assert number["number_max"] == Decimal("30.000000")
    assert number["number_sum"] == Decimal("60.000000")
    assert number["number_average"] == Decimal("20.000000")

    select = by_id[report_schema["select"].id]
    assert select["answered_count"] == 2
    assert select["unanswered_count"] == 1
    assert select["percentage_denominator_count"] == 2
    assert [(item["count"], item["percentage"]) for item in select["options"]] == [
        (1, Decimal("50.00")),
        (1, Decimal("50.00")),
    ]

    checkbox = by_id[report_schema["checkbox"].id]
    assert checkbox["answered_count"] == 2
    assert checkbox["unanswered_count"] == 1
    assert checkbox["percentage_denominator_count"] == 2
    assert [(item["count"], item["percentage"]) for item in checkbox["options"]] == [
        (2, Decimal("100.00")),
        (1, Decimal("50.00")),
    ]
    assert "do not have to sum to 100%" in checkbox["checkbox_percentage_note"]


@pytest.mark.django_db
def test_report_summary_uses_constant_query_count_across_questions(
    django_assert_num_queries,
    user,
    report_schema,
):
    cache.clear()

    with django_assert_num_queries(8):
        report = get_form_report_summary(owner=user, form_id=report_schema["form"].id)

    assert len(report["questions"]) == 4


@pytest.mark.django_db
def test_report_summary_cache_keeps_submission_aggregate_but_view_count_is_live(
    user,
    report_schema,
):
    cache.clear()
    first = get_form_report_summary(owner=user, form_id=report_schema["form"].id)

    Form.objects.filter(pk=report_schema["form"].pk).update(view_count=15)
    second = get_form_report_summary(owner=user, form_id=report_schema["form"].id)

    assert first["total_submissions"] == second["total_submissions"] == 0
    assert first["view_count"] == 9
    assert second["view_count"] == 15


@pytest.mark.django_db
def test_successful_submission_invalidates_cached_report_after_commit(
    user,
    report_schema,
    django_capture_on_commit_callbacks,
):
    cache.clear()
    before = get_form_report_summary(owner=user, form_id=report_schema["form"].id)
    key = form_report_cache_key(form_public_id=report_schema["form"].public_id)
    assert before["total_submissions"] == 0
    assert cache.get(key) is not None

    with django_capture_on_commit_callbacks(execute=True):
        _submit(report_schema, number=11)

    assert cache.get(key) is None
    after = get_form_report_summary(owner=user, form_id=report_schema["form"].id)
    assert after["total_submissions"] == 1


@pytest.mark.django_db
def test_report_cache_outage_falls_back_to_database(user, report_schema):
    with (
        patch("apps.forms.report_cache.cache.get", side_effect=RuntimeError("down")),
        patch("apps.forms.report_cache.cache.set", side_effect=RuntimeError("down")),
    ):
        report = get_form_report_summary(owner=user, form_id=report_schema["form"].id)

    assert report["title"] == "Report survey"
    assert report["total_submissions"] == 0


@pytest.mark.django_db
def test_report_owner_isolation_returns_none_for_foreign_owner(
    other_user,
    report_schema,
):
    assert (
        get_form_report_summary(
            owner=other_user,
            form_id=report_schema["form"].id,
        )
        is None
    )


@pytest.mark.django_db
def test_response_detail_prefetches_values_without_exposing_identity(
    user,
    report_respondent,
    report_schema,
):
    submission = _submit(
        report_schema,
        text="private response text",
        number=42,
        select=report_schema["select_a"],
        checkbox=[report_schema["check_b"]],
        respondent=report_respondent,
    )

    detail = get_form_report_submission_detail(
        owner=user,
        form_id=report_schema["form"].id,
        submission_public_id=submission.public_id,
    )

    assert detail["respondent_type"] == "authenticated"
    assert "respondent" not in detail
    assert "email" not in detail
    by_question = {answer["question_id"]: answer for answer in detail["answers"]}
    assert by_question[report_schema["text"].id]["text_value"] == "private response text"
    assert by_question[report_schema["number"].id]["number_value"] == Decimal("42.000000")
    assert by_question[report_schema["select"].id]["selected_options"][0]["label"] == "A"


@pytest.mark.django_db
def test_anonymous_response_detail_reports_only_anonymous_classification(user, report_schema):
    submission = _submit(report_schema, number=5)

    detail = get_form_report_submission_detail(
        owner=user,
        form_id=report_schema["form"].id,
        submission_public_id=submission.public_id,
    )

    assert detail["respondent_type"] == "anonymous"
    assert "respondent_id" not in detail
