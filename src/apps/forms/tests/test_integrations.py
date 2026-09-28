import pytest
from django.utils import timezone

from apps.core.integrations import form_has_active_process_runs
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
