import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from apps.forms.models import Form, FormSubmission
from apps.processes.models import Process, ProcessRun, ProcessStep, ProcessStepRun
from apps.processes.report_selectors import (
    get_process_report_run_detail,
    get_process_report_summary,
)

User = get_user_model()


def _run(*, process, respondent=None, status=ProcessRun.Status.IN_PROGRESS, token="token"):
    return ProcessRun.objects.create(
        process=process,
        respondent=respondent,
        resume_token_hash=None if respondent is not None else token,
        status=status,
        completed_at=timezone.now() if status == ProcessRun.Status.COMPLETED else None,
    )


@pytest.mark.django_db
def test_process_report_summary_no_runs(linear_process, user):
    summary = get_process_report_summary(owner=user, process_id=linear_process.pk)

    assert summary["total_runs"] == 0
    assert summary["completed_runs"] == 0
    assert summary["in_progress_runs"] == 0
    assert summary["completion_rate"] == 0
    assert summary["steps"][0]["completed_count"] == 0


@pytest.mark.django_db
def test_process_report_summary_linear_metrics(linear_process, published_form, user):
    step = linear_process.steps.get()

    completed = _run(
        process=linear_process,
        respondent=user,
        status=ProcessRun.Status.COMPLETED,
    )
    submission = FormSubmission.objects.create(form=published_form, respondent=user)
    ProcessStepRun.objects.create(
        process_run=completed,
        process_step=step,
        submission=submission,
        status=ProcessStepRun.Status.COMPLETED,
        completed_at=timezone.now(),
    )

    active = _run(process=linear_process, token="anonymous-linear")
    ProcessStepRun.objects.create(
        process_run=active,
        process_step=step,
        status=ProcessStepRun.Status.AVAILABLE,
    )

    summary = get_process_report_summary(owner=user, process_id=linear_process.pk)

    assert summary["total_runs"] == 2
    assert summary["completed_runs"] == 1
    assert summary["in_progress_runs"] == 1
    assert summary["response_count"] == 1
    assert summary["completion_rate"] == 50
    assert summary["steps"][0]["completed_count"] == 1
    assert summary["steps"][0]["available_count"] == 1
    assert {item["respondent_type"] for item in summary["recent_activity"]} == {
        "authenticated",
        "anonymous",
    }


@pytest.mark.django_db
def test_process_report_summary_free_step_distribution(user):
    first = Form.objects.create(owner=user, title="First", status=Form.Status.PUBLISHED)
    second = Form.objects.create(owner=user, title="Second", status=Form.Status.PUBLISHED)
    process = Process.objects.create(
        owner=user,
        title="Free report",
        process_type=Process.ProcessType.FREE,
        status=Process.Status.PUBLISHED,
    )
    step_one = ProcessStep.objects.create(process=process, form=first, order=1)
    step_two = ProcessStep.objects.create(process=process, form=second, order=2)
    run = _run(process=process, token="free-token")
    submission = FormSubmission.objects.create(form=second)
    ProcessStepRun.objects.create(
        process_run=run,
        process_step=step_one,
        status=ProcessStepRun.Status.AVAILABLE,
    )
    ProcessStepRun.objects.create(
        process_run=run,
        process_step=step_two,
        submission=submission,
        status=ProcessStepRun.Status.COMPLETED,
        completed_at=timezone.now(),
    )

    summary = get_process_report_summary(owner=user, process_id=process.pk)

    assert summary["process_type"] == Process.ProcessType.FREE
    assert summary["total_runs"] == 1
    assert summary["in_progress_runs"] == 1
    assert summary["steps"][0]["available_count"] == 1
    assert summary["steps"][1]["completed_count"] == 1


@pytest.mark.django_db
def test_process_report_cache_revision_refreshes_after_new_run(linear_process, user):
    cache.clear()
    first = get_process_report_summary(owner=user, process_id=linear_process.pk)
    assert first["total_runs"] == 0

    _run(process=linear_process, token="new-run")

    second = get_process_report_summary(owner=user, process_id=linear_process.pk)
    assert second["total_runs"] == 1


@pytest.mark.django_db
def test_process_report_owner_isolation(linear_process):
    other = User.objects.create_user(username="other-report-owner", password="password123")

    assert get_process_report_summary(owner=other, process_id=linear_process.pk) is None


@pytest.mark.django_db
def test_run_detail_exposes_safe_submission_reference_only(
    linear_process,
    published_form,
    user,
):
    step = linear_process.steps.get()
    run = _run(process=linear_process, token="secret-resume-hash")
    submission = FormSubmission.objects.create(form=published_form)
    ProcessStepRun.objects.create(
        process_run=run,
        process_step=step,
        submission=submission,
        status=ProcessStepRun.Status.COMPLETED,
        completed_at=timezone.now(),
    )

    detail = get_process_report_run_detail(
        owner=user,
        process_id=linear_process.pk,
        run_public_id=run.public_id,
    )

    assert detail["respondent_type"] == "anonymous"
    assert detail["steps"][0]["submission"]["public_id"] == submission.public_id
    assert "secret-resume-hash" not in repr(detail)
