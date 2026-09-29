from django.db.models import F, Prefetch

from apps.core.participant_access import (
    participant_cache_key,
    safe_cache_get,
    safe_cache_set,
)
from apps.forms.models import Form

from .models import Process, ProcessStep

RESOURCE_TYPE = "process"


def get_published_process_by_public_id(*, public_id):
    process = (
        Process.objects.filter(
            public_id=public_id,
            status=Process.Status.PUBLISHED,
        )
        .select_related("category")
        .first()
    )
    if process is None:
        return None

    if (
        process.visibility == Process.Visibility.PUBLIC
        and process.steps.filter(form__visibility=Form.Visibility.PRIVATE).exists()
    ):
        return None

    return process


def increment_process_view_count(*, process_id):
    Process.objects.filter(pk=process_id, status=Process.Status.PUBLISHED).update(
        view_count=F("view_count") + 1
    )


def _build_process_participant_read_model(*, process):
    process = (
        Process.objects.filter(pk=process.pk)
        .prefetch_related(
            Prefetch(
                "steps",
                queryset=ProcessStep.objects.select_related("form").order_by("order", "id"),
            )
        )
        .get()
    )

    return {
        "public_id": str(process.public_id),
        "title": process.title,
        "description": process.description,
        "process_type": process.process_type,
        "visibility": process.visibility,
        "status": process.status,
        "steps": [
            {
                "id": step.id,
                "order": step.order,
                "form_public_id": str(step.form.public_id),
            }
            for step in process.steps.all()
        ],
    }


def get_process_participant_read_model(*, process):
    key = participant_cache_key(resource_type=RESOURCE_TYPE, public_id=process.public_id)
    cached = safe_cache_get(key)
    if cached is not None:
        return cached

    read_model = _build_process_participant_read_model(process=process)
    safe_cache_set(key, read_model)
    return read_model
