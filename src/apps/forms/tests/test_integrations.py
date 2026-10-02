import pytest
from django.db import transaction
from django.utils import timezone

from apps.core.integrations import (
    form_has_active_process_runs,
    lock_required_forms_for_process_run,
)
from apps.forms.models import Form
from apps.processes.models import Process, ProcessRun, ProcessStep


@pytest.mark.django_db
def test_active_process_run_dependency_is_detected(user):
    form = Form.objects.create(
        owner=user,
        title="Published form",
        status=Form.Status.PUBLISHED,
    )
    process = Process.objects.create(
        owner=user,
        title="Process",
        process_type=Process.ProcessType.LINEAR,
        status=Process.Status.PUBLISHED,
    )
    ProcessStep.objects.create(process=process, form=form, order=1)
    run = ProcessRun.objects.create(process=process, respondent=user)

    assert form_has_active_process_runs(form_id=form.id) is True

    run.status = ProcessRun.Status.COMPLETED
    run.completed_at = timezone.now()
    run.save(update_fields=["status", "completed_at"])

    assert form_has_active_process_runs(form_id=form.id) is False


@pytest.mark.django_db
def test_process_run_lock_protocol_returns_required_forms_in_stable_order(user):
    first_form = Form.objects.create(owner=user, title="First")
    second_form = Form.objects.create(owner=user, title="Second")
    process = Process.objects.create(
        owner=user,
        title="Process",
        process_type=Process.ProcessType.LINEAR,
    )
    ProcessStep.objects.create(process=process, form=second_form, order=1)
    ProcessStep.objects.create(process=process, form=first_form, order=2)

    with transaction.atomic():
        locked_forms = lock_required_forms_for_process_run(process_id=process.id)

    assert [form.id for form in locked_forms] == sorted([first_form.id, second_form.id])
