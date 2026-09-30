import re

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.forms.models import Form, Question
from apps.processes.models import Process, ProcessRun, ProcessStepRun
from apps.processes.services import (
    close_process,
    create_process,
    create_process_step,
    publish_process,
)

User = get_user_model()


def _published_linear_process(*, owner, visibility=Process.Visibility.PUBLIC):
    form1 = Form.objects.create(
        owner=owner,
        title="Identity form",
        status=Form.Status.PUBLISHED,
    )
    question1 = Question.objects.create(
        form=form1,
        text="Your name?",
        question_type=Question.QuestionType.TEXT,
        order=1,
        is_required=True,
    )
    form2 = Form.objects.create(
        owner=owner,
        title="Age form",
        status=Form.Status.PUBLISHED,
    )
    question2 = Question.objects.create(
        form=form2,
        text="Your age?",
        question_type=Question.QuestionType.NUMBER,
        order=1,
        is_required=True,
    )

    kwargs = {
        "owner": owner,
        "title": "Participant onboarding",
        "process_type": Process.ProcessType.LINEAR,
        "visibility": visibility,
    }
    if visibility == Process.Visibility.PRIVATE:
        kwargs["access_password"] = "process-secret"

    process = create_process(**kwargs)
    step1 = create_process_step(process=process, owner=owner, form_id=form1.pk)
    step2 = create_process_step(process=process, owner=owner, form_id=form2.pk)
    publish_process(process=process, owner=owner)
    return process, step1, step2, question1, question2


def _extract_resume_token(response):
    match = re.search(
        rb'<code id="resume-token-once">([^<]+)</code>',
        response.content,
    )
    assert match is not None
    return match.group(1).decode()


@pytest.mark.django_db
def test_anonymous_html_start_shows_resume_token_once_and_keeps_token_out_of_url(user):
    process, *_ = _published_linear_process(owner=user)
    client = Client()

    start = client.post(reverse("processes_participant:run_start", args=[process.public_id]))

    assert start.status_code == 302
    run = ProcessRun.objects.get(process=process)
    assert run.respondent_id is None
    assert run.resume_token_hash
    assert str(run.public_id) in start.url

    first_detail = client.get(start.url)
    assert first_detail.status_code == 200
    assert "no-store" in first_detail["Cache-Control"]
    raw_token = _extract_resume_token(first_detail)
    assert raw_token not in start.url
    assert raw_token not in str(run.resume_token_hash)

    refreshed = client.get(start.url)
    assert refreshed.status_code == 200
    assert b"resume-token-once" not in refreshed.content


@pytest.mark.django_db
def test_anonymous_html_resume_works_from_fresh_session(user):
    process, *_ = _published_linear_process(owner=user)
    first_client = Client()
    start = first_client.post(reverse("processes_participant:run_start", args=[process.public_id]))
    raw_token = _extract_resume_token(first_client.get(start.url))
    run = ProcessRun.objects.get(process=process)

    fresh_client = Client()
    resume = fresh_client.post(
        reverse("processes_participant:resume", args=[process.public_id]),
        {"resume_token": raw_token},
    )

    assert resume.status_code == 302
    assert str(run.public_id) in resume.url
    assert raw_token not in resume.url
    assert fresh_client.get(resume.url).status_code == 200


@pytest.mark.django_db
def test_invalid_resume_token_does_not_grant_anonymous_run(user):
    process, *_ = _published_linear_process(owner=user)
    client = Client()

    response = client.post(
        reverse("processes_participant:resume", args=[process.public_id]),
        {"resume_token": "not-the-token"},
    )

    assert response.status_code == 400
    assert b"not valid for this process" in response.content


@pytest.mark.django_db
def test_authenticated_html_run_is_owner_scoped(user):
    process, *_ = _published_linear_process(owner=user)
    participant = User.objects.create_user(
        username="participant-html",
        email="participant-html@example.com",
        password="password123",
    )
    other = User.objects.create_user(
        username="other-html",
        email="other-html@example.com",
        password="password123",
    )

    client = Client()
    client.force_login(participant)
    client.post(reverse("processes_participant:run_start", args=[process.public_id]))
    run = ProcessRun.objects.get(process=process)
    assert run.respondent == participant
    assert run.resume_token_hash is None

    other_client = Client()
    other_client.force_login(other)
    denied = other_client.get(
        reverse(
            "processes_participant:run_detail",
            args=[process.public_id, run.public_id],
        )
    )
    assert denied.status_code == 403

    landing = client.get(reverse("processes_participant:detail", args=[process.public_id]))
    assert landing.status_code == 200
    assert b"Continue your run" in landing.content


@pytest.mark.django_db
def test_linear_html_steps_lock_advance_and_complete(user):
    process, step1, step2, question1, question2 = _published_linear_process(owner=user)
    client = Client()
    start = client.post(reverse("processes_participant:run_start", args=[process.public_id]))
    run = ProcessRun.objects.get(process=process)
    client.get(start.url)

    locked = client.get(
        reverse(
            "processes_participant:step",
            args=[process.public_id, run.public_id, step2.pk],
        )
    )
    assert locked.status_code == 409
    assert b"locked" in locked.content.lower()

    step1_url = reverse(
        "processes_participant:step",
        args=[process.public_id, run.public_id, step1.pk],
    )
    first_page = client.get(step1_url)
    assert first_page.status_code == 200
    assert b"Your name?" in first_page.content

    first_submit = client.post(
        step1_url,
        {f"q_{question1.pk}": "Ada"},
    )
    assert first_submit.status_code == 302

    states = list(
        ProcessStepRun.objects.filter(process_run=run)
        .order_by("process_step__order")
        .values_list("status", flat=True)
    )
    assert states == [
        ProcessStepRun.Status.COMPLETED,
        ProcessStepRun.Status.AVAILABLE,
    ]

    step2_url = reverse(
        "processes_participant:step",
        args=[process.public_id, run.public_id, step2.pk],
    )
    second_submit = client.post(
        step2_url,
        {f"q_{question2.pk}": "30"},
    )
    assert second_submit.status_code == 302

    run.refresh_from_db()
    assert run.status == ProcessRun.Status.COMPLETED
    assert run.completed_at is not None
    receipt = client.get(second_submit.url)
    assert receipt.status_code == 200
    assert b"Process completed" in receipt.content


@pytest.mark.django_db
def test_step_validation_errors_are_rendered_without_advancing_run(user):
    process, step1, _, question1, _ = _published_linear_process(owner=user)
    client = Client()
    start = client.post(reverse("processes_participant:run_start", args=[process.public_id]))
    run = ProcessRun.objects.get(process=process)
    client.get(start.url)

    step1_url = reverse(
        "processes_participant:step",
        args=[process.public_id, run.public_id, step1.pk],
    )
    response = client.post(step1_url, {f"q_{question1.pk}": ""})

    assert response.status_code == 400
    assert b"Check your answers" in response.content
    step_run = ProcessStepRun.objects.get(process_run=run, process_step=step1)
    assert step_run.status == ProcessStepRun.Status.AVAILABLE
    assert step_run.submission_id is None


@pytest.mark.django_db
def test_private_closed_process_can_unlock_and_resume_existing_anonymous_run(user):
    process, *_ = _published_linear_process(
        owner=user,
        visibility=Process.Visibility.PRIVATE,
    )
    first_client = Client()
    unlock = first_client.post(
        reverse("processes_participant:unlock", args=[process.public_id]),
        {"password": "process-secret"},
    )
    assert unlock.status_code == 302

    start = first_client.post(reverse("processes_participant:run_start", args=[process.public_id]))
    raw_token = _extract_resume_token(first_client.get(start.url))
    run = ProcessRun.objects.get(process=process)

    close_process(process=process, owner=user)
    process.refresh_from_db()
    assert process.status == Process.Status.CLOSED

    fresh_client = Client()
    resume_page = fresh_client.get(
        reverse("processes_participant:resume", args=[process.public_id])
    )
    assert resume_page.status_code == 403
    assert b'name="next" value="resume"' in resume_page.content

    unlock_resume = fresh_client.post(
        reverse("processes_participant:unlock", args=[process.public_id]),
        {
            "password": "process-secret",
            "next": "resume",
        },
    )
    assert unlock_resume.status_code == 302
    assert unlock_resume.url == reverse(
        "processes_participant:resume",
        args=[process.public_id],
    )

    resumed = fresh_client.post(
        unlock_resume.url,
        {"resume_token": raw_token},
    )
    assert resumed.status_code == 302
    assert str(run.public_id) in resumed.url
    assert fresh_client.get(resumed.url).status_code == 200


@pytest.mark.django_db
def test_closed_process_still_rejects_new_html_run(user):
    process, *_ = _published_linear_process(owner=user)
    close_process(process=process, owner=user)

    response = Client().post(reverse("processes_participant:run_start", args=[process.public_id]))

    assert response.status_code == 404
