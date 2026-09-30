import pytest
from django.core.cache import cache

from apps.forms.models import Form
from apps.processes.models import Process, ProcessStep
from apps.processes.report_selectors import get_process_report_summary


@pytest.mark.django_db
def test_draft_process_report_does_not_cache_mutable_step_schema(user):
    cache.clear()
    process = Process.objects.create(
        owner=user,
        title="Mutable draft report",
        process_type=Process.ProcessType.LINEAR,
        status=Process.Status.DRAFT,
    )

    before = get_process_report_summary(owner=user, process_id=process.pk)
    assert before["steps"] == []

    form = Form.objects.create(
        owner=user,
        title="Fresh draft step",
        status=Form.Status.DRAFT,
    )
    step = ProcessStep.objects.create(process=process, form=form, order=1)

    after_add = get_process_report_summary(owner=user, process_id=process.pk)
    assert [item["id"] for item in after_add["steps"]] == [step.pk]
    assert after_add["steps"][0]["form_title"] == "Fresh draft step"

    form.title = "Renamed draft step"
    form.save(update_fields=["title", "updated_at"])

    after_rename = get_process_report_summary(owner=user, process_id=process.pk)
    assert after_rename["steps"][0]["form_title"] == "Renamed draft step"
