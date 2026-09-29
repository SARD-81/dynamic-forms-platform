from django.db.models import F, Prefetch

from apps.core.participant_access import (
    participant_cache_key,
    safe_cache_get,
    safe_cache_set,
)
from apps.forms.models import Form

from .models import Process, ProcessRun, ProcessStep, ProcessStepRun

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


def get_executable_process_by_public_id(*, public_id):
    """
    پروسه را برای ادامه اجرای ران‌های قبلی دریافت می‌کند (فقط PUBLISHED یا CLOSED).
    این سلکتور به تنهایی پروسه CLOSED را قابل شروع مجدد نمی‌‌کند.
    """
    process = (
        Process.objects.filter(
            public_id=public_id,
            status__in=[Process.Status.PUBLISHED, Process.Status.CLOSED],
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


def get_process_run_for_process(*, process, run_public_id):
    """
    یک ProcessRun را اسکوپ‌شده به پروسه جاری همراه با اطلاعات شرکت‌کننده
    و استپ‌های مرتب‌شده واکشی می‌کند. در صورت عدم تطابق با پروسه None برمی‌گرداند.
    """
    return (
        ProcessRun.objects.filter(
            process=process,
            public_id=run_public_id,
        )
        .select_related("process", "respondent")
        .prefetch_related(
            Prefetch(
                "step_runs",
                queryset=ProcessStepRun.objects.select_related(
                    "process_step", "process_step__form"
                ).order_by("process_step__order", "id"),
            )
        )
        .first()
    )


def get_in_progress_process_run_for_respondent(*, process, respondent):
    """
    آخرین ران در حال اجرای کاربر احراز هویت شده را دریافت می‌کند (برای نمایش دکمه ادامه در HTML).
    """
    if respondent is None or not respondent.is_authenticated:
        return None

    return (
        ProcessRun.objects.filter(
            process=process,
            respondent=respondent,
            status=ProcessRun.Status.IN_PROGRESS,
        )
        .select_related("process", "respondent")
        .prefetch_related(
            Prefetch(
                "step_runs",
                queryset=ProcessStepRun.objects.select_related(
                    "process_step", "process_step__form"
                ).order_by("process_step__order", "id"),
            )
        )
        .order_by("-started_at", "-id")
        .first()
    )


def get_process_run_by_token_hash(*, process, resume_token_hash):
    """
    یک ProcessRun ناشناس را منحصراً بر اساس هش SHA-256 توکن بازیابی دریافت می‌کند.
    توکن خام هرگز در این لایه لاگ یا ذخیره نمی‌شود.
    """
    if not resume_token_hash:
        return None

    return (
        ProcessRun.objects.filter(
            process=process,
            resume_token_hash=resume_token_hash,
        )
        .select_related("process", "respondent")
        .prefetch_related(
            Prefetch(
                "step_runs",
                queryset=ProcessStepRun.objects.select_related(
                    "process_step", "process_step__form"
                ).order_by("process_step__order", "id"),
            )
        )
        .first()
    )


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
