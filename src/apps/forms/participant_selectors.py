from django.db.models import F, Prefetch

from apps.core.participant_access import (
    participant_cache_key,
    safe_cache_get,
    safe_cache_set,
)

from .models import Form, Question, QuestionOption

RESOURCE_TYPE = "form"


def get_published_form_by_public_id(*, public_id):
    return (
        Form.objects.filter(
            public_id=public_id,
            status=Form.Status.PUBLISHED,
        )
        .select_related("category")
        .first()
    )


def increment_form_view_count(*, form_id):
    Form.objects.filter(pk=form_id, status=Form.Status.PUBLISHED).update(
        view_count=F("view_count") + 1
    )


def _build_form_participant_read_model(*, form):
    questions = (
        Question.objects.filter(form=form)
        .prefetch_related(
            Prefetch(
                "options",
                queryset=QuestionOption.objects.order_by("order", "id"),
            )
        )
        .order_by("order", "id")
    )

    return {
        "public_id": str(form.public_id),
        "title": form.title,
        "description": form.description,
        "visibility": form.visibility,
        "status": form.status,
        "questions": [
            {
                "id": question.id,
                "text": question.text,
                "question_type": question.question_type,
                "is_required": question.is_required,
                "order": question.order,
                "max_length": question.max_length,
                "min_value": str(question.min_value) if question.min_value is not None else None,
                "max_value": str(question.max_value) if question.max_value is not None else None,
                "options": [
                    {
                        "id": option.id,
                        "label": option.label,
                        "order": option.order,
                    }
                    for option in question.options.all()
                ],
            }
            for question in questions
        ],
    }


def get_form_participant_read_model(*, form):
    key = participant_cache_key(resource_type=RESOURCE_TYPE, public_id=form.public_id)
    cached = safe_cache_get(key)
    if cached is not None:
        return cached

    read_model = _build_form_participant_read_model(form=form)
    safe_cache_set(key, read_model)
    return read_model
