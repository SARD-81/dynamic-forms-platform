import pytest
from django.test import Client
from django.urls import reverse

from apps.forms.models import Form, Question
from apps.processes.models import Process, ProcessRun, ProcessStepRun
from apps.processes.participant_views import RUN_TOKEN_ONCE_SESSION_KEY
from apps.processes.services import create_process, create_process_step, publish_process


def _published_process(*, owner, process_type):
    first_form = Form.objects.create(
        owner=owner,
        title="First form",
        status=Form.Status.PUBLISHED,
    )
    first_question = Question.objects.create(
        form=first_form,
        text="First answer",
        question_type=Question.QuestionType.TEXT,
        order=1,
        is_required=True,
    )
    second_form = Form.objects.create(
        owner=owner,
        title="Second form",
        status=Form.Status.PUBLISHED,
    )
    second_question = Question.objects.create(
        form=second_form,
        text="Second answer",
        question_type=Question.QuestionType.TEXT,
        order=1,
        is_required=True,
    )

    process = create_process(
        owner=owner,
        title="Gate 3 hardening process",
        process_type=process_type,
    )
    first_step = create_process_step(process=process, owner=owner, form_id=first_form.pk)
    second_step = create_process_step(process=process, owner=owner, form_id=second_form.pk)
    publish_process(process=process, owner=owner)
    return process, first_step, second_step, first_question, second_question


@pytest.mark.django_db
def test_anonymous_resume_token_is_removed_from_session_after_first_display(user):
    process, *_ = _published_process(owner=user, process_type=Process.ProcessType.LINEAR)
    client = Client()

    start = client.post(reverse("processes_participant:run_start", args=[process.public_id]))
    assert start.status_code == 302

    pending_tokens = client.session.get(RUN_TOKEN_ONCE_SESSION_KEY, {})
    assert len(pending_tokens) == 1
    raw_token = next(iter(pending_tokens.values()))
    assert raw_token not in start.url

    first_display = client.get(start.url)
    assert first_display.status_code == 200
    assert raw_token.encode() in first_display.content
    assert b"held temporarily in your current session" in first_display.content
    assert b"never placed in the URL" in first_display.content

    remaining_tokens = client.session.get(RUN_TOKEN_ONCE_SESSION_KEY, {})
    assert remaining_tokens == {}
    assert raw_token not in str(remaining_tokens)

    refreshed = client.get(start.url)
    assert refreshed.status_code == 200
    assert raw_token.encode() not in refreshed.content


@pytest.mark.django_db
def test_free_process_html_can_complete_steps_in_arbitrary_order(user):
    process, first_step, second_step, first_question, second_question = _published_process(
        owner=user,
        process_type=Process.ProcessType.FREE,
    )
    client = Client()

    start = client.post(reverse("processes_participant:run_start", args=[process.public_id]))
    assert start.status_code == 302
    run = ProcessRun.objects.get(process=process)
    assert client.get(start.url).status_code == 200

    initial_states = list(
        ProcessStepRun.objects.filter(process_run=run)
        .order_by("process_step__order")
        .values_list("status", flat=True)
    )
    assert initial_states == [
        ProcessStepRun.Status.AVAILABLE,
        ProcessStepRun.Status.AVAILABLE,
    ]

    second_url = reverse(
        "processes_participant:step",
        args=[process.public_id, run.public_id, second_step.pk],
    )
    assert client.get(second_url).status_code == 200
    second_submit = client.post(
        second_url,
        {f"q_{second_question.pk}": "completed second first"},
    )
    assert second_submit.status_code == 302

    run.refresh_from_db()
    assert run.status == ProcessRun.Status.IN_PROGRESS
    middle_states = list(
        ProcessStepRun.objects.filter(process_run=run)
        .order_by("process_step__order")
        .values_list("status", flat=True)
    )
    assert middle_states == [
        ProcessStepRun.Status.AVAILABLE,
        ProcessStepRun.Status.COMPLETED,
    ]

    first_url = reverse(
        "processes_participant:step",
        args=[process.public_id, run.public_id, first_step.pk],
    )
    first_submit = client.post(
        first_url,
        {f"q_{first_question.pk}": "completed first second"},
    )
    assert first_submit.status_code == 302

    run.refresh_from_db()
    assert run.status == ProcessRun.Status.COMPLETED
    assert run.completed_at is not None
    final_states = list(
        ProcessStepRun.objects.filter(process_run=run)
        .order_by("process_step__order")
        .values_list("status", flat=True)
    )
    assert final_states == [
        ProcessStepRun.Status.COMPLETED,
        ProcessStepRun.Status.COMPLETED,
    ]

    receipt = client.get(first_submit.url)
    assert receipt.status_code == 200
    assert b"Process completed" in receipt.content
