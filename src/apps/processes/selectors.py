from django.db.models import Prefetch

from apps.forms.models import Form

from .models import Process, ProcessStep


def get_processes_for_owner(*, owner):
    """لیست تمام فرآیندهای کاربر همراه با دسته‌بندی و مراحل مرتب‌شده."""
    return (
        Process.objects.filter(owner=owner)
        .select_related("category")
        .prefetch_related(
            Prefetch(
                "steps",
                queryset=ProcessStep.objects.select_related("form").order_by("order", "id"),
            )
        )
        .order_by("-created_at", "-id")
    )


def get_process_for_owner(*, owner, process_id):
    """دریافت یک فرآیند مشخص متعلق به کاربر."""
    return get_processes_for_owner(owner=owner).filter(pk=process_id).first()


def get_process_steps_for_owner(*, owner, process_id):
    """دریافت تمام مراحل یک فرآیند متعلق به کاربر با ترتیب قطعی."""
    return (
        ProcessStep.objects.filter(
            process_id=process_id,
            process__owner=owner,
        )
        .select_related("form")
        .order_by("order", "id")
    )


def get_process_step_for_owner(*, owner, process_id, step_id):
    """دریافت یک مرحله مشخص از فرآیند متعلق به کاربر."""
    return (
        get_process_steps_for_owner(
            owner=owner,
            process_id=process_id,
        )
        .filter(pk=step_id)
        .first()
    )


def get_available_forms_for_owner(*, owner):
    """فرم‌های مجاز متعلق به کاربر جهت اتصال به مراحل فرآیند."""
    return Form.objects.filter(owner=owner).order_by("title", "id")
