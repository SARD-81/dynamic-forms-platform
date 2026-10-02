import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.forms.models import FormSubmission
from apps.processes.models import ProcessRun, ProcessStepRun

User = get_user_model()


@pytest.fixture
def report_run(linear_process, published_form, user):
    step = linear_process.steps.get()
    run = ProcessRun.objects.create(
        process=linear_process,
        respondent=user,
        resume_token_hash=None,
    )
    submission = FormSubmission.objects.create(form=published_form, respondent=user)
    ProcessStepRun.objects.create(
        process_run=run,
        process_step=step,
        submission=submission,
        status=ProcessStepRun.Status.COMPLETED,
        completed_at=timezone.now(),
    )
    return run, submission


@pytest.mark.django_db
def test_process_report_html_dashboard_runs_and_detail(linear_process, user, report_run):
    run, _ = report_run
    client = Client()
    client.force_login(user)

    dashboard = client.get(reverse("processes:report", args=[linear_process.pk]))
    runs = client.get(reverse("processes:report_runs", args=[linear_process.pk]))
    detail = client.get(
        reverse(
            "processes:report_run_detail",
            args=[linear_process.pk, run.public_id],
        )
    )

    assert dashboard.status_code == 200
    assert b"Runs started" in dashboard.content
    assert b"Step analytics" in dashboard.content
    assert runs.status_code == 200
    assert b"Authenticated" in runs.content
    assert detail.status_code == 200
    assert b"View linked Form response" in detail.content


@pytest.mark.django_db
def test_process_report_html_is_owner_scoped(linear_process):
    other = User.objects.create_user(username="html-report-other", password="password123")
    client = Client()
    client.force_login(other)

    response = client.get(reverse("processes:report", args=[linear_process.pk]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_process_detail_links_to_report(linear_process, user):
    client = Client()
    client.force_login(user)

    response = client.get(reverse("processes:detail", args=[linear_process.pk]))

    assert response.status_code == 200
    assert reverse("processes:report", args=[linear_process.pk]).encode() in response.content


@pytest.mark.django_db
def test_process_report_api_summary_list_and_detail(linear_process, user, report_run):
    run, submission = report_run
    ProcessRun.objects.filter(pk=run.pk).update(resume_token_hash=None)
    client = APIClient()
    client.force_authenticate(user=user)

    summary = client.get(f"/api/v1/processes/{linear_process.pk}/report/")
    runs = client.get(f"/api/v1/processes/{linear_process.pk}/runs/")
    detail = client.get(f"/api/v1/processes/{linear_process.pk}/runs/{run.public_id}/")

    assert summary.status_code == 200
    assert summary.data["total_runs"] == 1
    assert runs.status_code == 200
    assert runs.data["count"] == 1
    assert runs.data["results"][0]["respondent_type"] == "authenticated"
    assert detail.status_code == 200
    assert detail.data["steps"][0]["submission"]["public_id"] == str(submission.public_id)
    assert "resume_token" not in str(detail.data).lower()


@pytest.mark.django_db
def test_process_report_api_is_owner_scoped(linear_process):
    other = User.objects.create_user(username="api-report-other", password="password123")
    client = APIClient()
    client.force_authenticate(user=other)

    assert client.get(f"/api/v1/processes/{linear_process.pk}/report/").status_code == 404
    assert client.get(f"/api/v1/processes/{linear_process.pk}/runs/").status_code == 404


@pytest.mark.django_db
def test_process_report_api_requires_authentication(linear_process):
    client = APIClient()

    assert client.get(f"/api/v1/processes/{linear_process.pk}/report/").status_code in {401, 403}
