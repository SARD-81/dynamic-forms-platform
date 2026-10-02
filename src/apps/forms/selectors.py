from django.db.models import Prefetch

from .models import Form, Question, QuestionOption


def get_forms_for_owner(*, owner):
    return (
        Form.objects.filter(owner=owner).select_related("category").order_by("-created_at", "-id")
    )


def get_form_for_owner(*, owner, form_id):
    return get_forms_for_owner(owner=owner).filter(pk=form_id).first()


def get_questions_for_form_owner(*, owner, form_id):
    return (
        Question.objects.filter(form_id=form_id, form__owner=owner)
        .prefetch_related(
            Prefetch(
                "options",
                queryset=QuestionOption.objects.order_by("order", "id"),
            )
        )
        .order_by("order", "id")
    )


def get_question_for_owner(*, owner, form_id, question_id):
    return get_questions_for_form_owner(owner=owner, form_id=form_id).filter(pk=question_id).first()


def get_options_for_question_owner(*, owner, form_id, question_id):
    return QuestionOption.objects.filter(
        question_id=question_id,
        question__form_id=form_id,
        question__form__owner=owner,
    ).order_by("order", "id")


def get_option_for_owner(*, owner, form_id, question_id, option_id):
    return (
        get_options_for_question_owner(
            owner=owner,
            form_id=form_id,
            question_id=question_id,
        )
        .filter(pk=option_id)
        .first()
    )
