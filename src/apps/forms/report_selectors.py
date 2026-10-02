from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Avg, Count, Max, Min, Prefetch, Sum
from django.db.models.functions import TruncDate

from .models import (
    Answer,
    AnswerOption,
    Form,
    FormSubmission,
    Question,
    QuestionOption,
)
from .report_cache import get_cached_form_report, set_cached_form_report
from .selectors import get_form_for_owner

FORM_REPORT_RECENT_LIMIT = 5
FORM_REPORT_TIMELINE_DAYS = 14
FORM_REPORT_PAGE_SIZE = 20


def _percentage(*, count, denominator):
    if not denominator:
        return Decimal("0.00")
    return ((Decimal(count) * Decimal("100")) / Decimal(denominator)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _report_decimal(value):
    if value is None:
        return None
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _form_submission_revision(*, form):
    return FormSubmission.objects.filter(form_id=form.pk).aggregate(
        submission_count=Count("id"),
        latest_submission_id=Max("id"),
    )


def _build_submission_aggregate(*, form, total_submissions=None):
    submissions = FormSubmission.objects.filter(form_id=form.pk)
    if total_submissions is None:
        total_submissions = submissions.count()

    recent_activity = [
        {
            "public_id": row["public_id"],
            "submitted_at": row["submitted_at"],
            "respondent_type": (
                "authenticated" if row["respondent_id"] is not None else "anonymous"
            ),
        }
        for row in submissions.order_by("-submitted_at", "-id").values(
            "public_id",
            "submitted_at",
            "respondent_id",
        )[:FORM_REPORT_RECENT_LIMIT]
    ]

    timeline_rows = list(
        submissions.annotate(day=TruncDate("submitted_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("-day")[:FORM_REPORT_TIMELINE_DAYS]
    )
    timeline = [{"date": row["day"], "count": row["count"]} for row in reversed(timeline_rows)]

    questions = list(
        Question.objects.filter(form_id=form.pk)
        .prefetch_related(
            Prefetch(
                "options",
                queryset=QuestionOption.objects.order_by("order", "id"),
            )
        )
        .order_by("order", "id")
    )

    answer_stats = {
        row["question_id"]: row
        for row in (
            Answer.objects.filter(submission__form_id=form.pk)
            .values("question_id")
            .annotate(
                answered_count=Count("id"),
                number_min=Min("number_value"),
                number_max=Max("number_value"),
                number_sum=Sum("number_value"),
                number_average=Avg("number_value"),
            )
        )
    }

    option_counts = {
        row["option_id"]: row["selected_count"]
        for row in (
            AnswerOption.objects.filter(answer__submission__form_id=form.pk)
            .values("option_id")
            .annotate(selected_count=Count("id"))
        )
    }

    question_analytics = []
    for question in questions:
        stats = answer_stats.get(question.pk, {})
        answered_count = stats.get("answered_count", 0)
        item = {
            "id": question.pk,
            "text": question.text,
            "question_type": question.question_type,
            "is_required": question.is_required,
            "order": question.order,
            "answered_count": answered_count,
            "unanswered_count": max(total_submissions - answered_count, 0),
            "percentage_denominator": "answered_submissions",
            "percentage_denominator_count": answered_count,
            "checkbox_percentage_note": "",
            "number_min": None,
            "number_max": None,
            "number_sum": None,
            "number_average": None,
            "options": [],
        }

        if question.question_type == Question.QuestionType.NUMBER:
            item.update(
                {
                    "number_min": _report_decimal(stats.get("number_min")),
                    "number_max": _report_decimal(stats.get("number_max")),
                    "number_sum": _report_decimal(stats.get("number_sum")),
                    "number_average": _report_decimal(stats.get("number_average")),
                }
            )

        if question.question_type in {
            Question.QuestionType.SELECT,
            Question.QuestionType.CHECKBOX,
        }:
            item["options"] = [
                {
                    "id": option.pk,
                    "label": option.label,
                    "order": option.order,
                    "count": option_counts.get(option.pk, 0),
                    "percentage": _percentage(
                        count=option_counts.get(option.pk, 0),
                        denominator=answered_count,
                    ),
                }
                for option in question.options.all()
            ]
            if question.question_type == Question.QuestionType.CHECKBOX:
                item["checkbox_percentage_note"] = (
                    "Percentages use submissions that answered this question as the "
                    "denominator. Multiple options may be selected, so option percentages "
                    "do not have to sum to 100%."
                )

        question_analytics.append(item)

    return {
        "total_submissions": total_submissions,
        "recent_activity": recent_activity,
        "timeline": timeline,
        "questions": question_analytics,
    }


def get_form_report_summary(*, owner, form_id):
    form = get_form_for_owner(owner=owner, form_id=form_id)
    if form is None:
        return None

    aggregate = None
    submission_revision = None
    if form.status != Form.Status.DRAFT:
        submission_revision = _form_submission_revision(form=form)
        aggregate = get_cached_form_report(
            form_public_id=form.public_id,
            submission_count=submission_revision["submission_count"],
            latest_submission_id=submission_revision["latest_submission_id"],
        )

    if aggregate is None:
        aggregate = _build_submission_aggregate(
            form=form,
            total_submissions=(
                submission_revision["submission_count"] if submission_revision is not None else None
            ),
        )
        if submission_revision is not None:
            set_cached_form_report(
                form_public_id=form.public_id,
                submission_count=submission_revision["submission_count"],
                latest_submission_id=submission_revision["latest_submission_id"],
                payload=aggregate,
            )

    return {
        "id": form.pk,
        "public_id": form.public_id,
        "title": form.title,
        "status": form.status,
        "view_count": form.view_count,
        **aggregate,
    }


def get_form_report_submissions(*, owner, form_id):
    return (
        FormSubmission.objects.filter(
            form_id=form_id,
            form__owner=owner,
        )
        .only(
            "id",
            "public_id",
            "form_id",
            "respondent_id",
            "submitted_at",
        )
        .order_by("-submitted_at", "-id")
    )


def submission_list_item(submission):
    return {
        "public_id": submission.public_id,
        "submitted_at": submission.submitted_at,
        "respondent_type": (
            "authenticated" if submission.respondent_id is not None else "anonymous"
        ),
    }


def get_form_report_submission_detail(*, owner, form_id, submission_public_id):
    answer_queryset = (
        Answer.objects.select_related("question")
        .prefetch_related(
            Prefetch(
                "selected_options",
                queryset=AnswerOption.objects.select_related("option").order_by(
                    "option__order",
                    "option__id",
                ),
            )
        )
        .order_by("question__order", "question_id")
    )

    submission = (
        FormSubmission.objects.filter(
            public_id=submission_public_id,
            form_id=form_id,
            form__owner=owner,
        )
        .prefetch_related(Prefetch("answers", queryset=answer_queryset))
        .first()
    )
    if submission is None:
        return None

    return {
        "public_id": submission.public_id,
        "submitted_at": submission.submitted_at,
        "respondent_type": (
            "authenticated" if submission.respondent_id is not None else "anonymous"
        ),
        "answers": [
            {
                "question_id": answer.question_id,
                "question_text": answer.question.text,
                "question_type": answer.question.question_type,
                "question_order": answer.question.order,
                "text_value": answer.text_value,
                "number_value": answer.number_value,
                "selected_options": [
                    {
                        "id": link.option_id,
                        "label": link.option.label,
                        "order": link.option.order,
                    }
                    for link in answer.selected_options.all()
                ],
            }
            for answer in submission.answers.all()
        ],
    }
