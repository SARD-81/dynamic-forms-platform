from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from apps.core.participant_access import invalidate_participant_read_model
from apps.forms.models import Form, Question
from apps.processes.models import Process, ProcessStep
from apps.processes.participant_selectors import get_process_participant_read_model
from apps.processes.services import close_process


@pytest.fixture
def process_form(user):
    form = Form.objects.create(
        owner=user,
        title="Step form",
        status=Form.Status.PUBLISHED,
    )
    Question.objects.create(
        form=form,
        text="Step question",
        question_type=Question.QuestionType.TEXT,
        order=1,
    )
    return form


@pytest.fixture
def public_process(user, process_form):
    process = Process.objects.create(
        owner=user,
        title="Public process",
        description="Published workflow",
        process_type=Process.ProcessType.LINEAR,
        visibility=Process.Visibility.PUBLIC,
        status=Process.Status.PUBLISHED,
    )
    ProcessStep.objects.create(process=process, form=process_form, order=1)
    return process


@pytest.fixture
def private_process(user, process_form):
    process = Process.objects.create(
        owner=user,
        title="Private process",
        process_type=Process.ProcessType.FREE,
        visibility=Process.Visibility.PRIVATE,
        access_password_hash=make_password("process-secret"),
        status=Process.Status.PUBLISHED,
    )
    ProcessStep.objects.create(process=process, form=process_form, order=1)
    return process


@pytest.mark.django_db
def test_public_process_is_anonymous_and_counts_successful_views(client, public_process):
    url = reverse("processes_participant:detail", args=[public_process.public_id])

    response = client.get(url)

    assert response.status_code == 200
    assert "Public process" in response.content.decode()
    public_process.refresh_from_db()
    assert public_process.view_count == 1

    head = client.head(url)
    rejected_post = client.post(url)
    public_process.refresh_from_db()

    assert head.status_code == 200
    assert rejected_post.status_code == 405

    api_head = client.head(f"/api/v1/public/processes/{public_process.public_id}/")
    public_process.refresh_from_db()

    assert api_head.status_code == 200
    assert public_process.view_count == 1


@pytest.mark.django_db
def test_public_process_with_private_step_form_fails_closed_for_participants(
    client,
    user,
):
    private_form = Form.objects.create(
        owner=user,
        title="Hidden step",
        visibility=Form.Visibility.PRIVATE,
        access_password_hash=make_password("hidden-secret"),
        status=Form.Status.PUBLISHED,
    )
    process = Process.objects.create(
        owner=user,
        title="Invalid public process",
        process_type=Process.ProcessType.LINEAR,
        visibility=Process.Visibility.PUBLIC,
        status=Process.Status.PUBLISHED,
    )
    ProcessStep.objects.create(process=process, form=private_form, order=1)

    assert (
        client.get(reverse("processes_participant:detail", args=[process.public_id])).status_code
        == 404
    )
    assert client.get(f"/api/v1/public/processes/{process.public_id}/").status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("resource_status", [Process.Status.DRAFT, Process.Status.CLOSED])
def test_non_published_process_is_not_participant_accessible(
    client,
    user,
    resource_status,
):
    process = Process.objects.create(
        owner=user,
        title="Unavailable process",
        process_type=Process.ProcessType.LINEAR,
        status=resource_status,
    )

    html = client.get(reverse("processes_participant:detail", args=[process.public_id]))
    api = client.get(f"/api/v1/public/processes/{process.public_id}/")

    assert html.status_code == 404
    assert api.status_code == 404
    process.refresh_from_db()
    assert process.view_count == 0


@pytest.mark.django_db
def test_private_process_wrong_and_correct_password(client, private_process):
    detail_url = f"/api/v1/public/processes/{private_process.public_id}/"
    unlock_url = f"{detail_url}unlock/"

    assert client.get(detail_url).status_code == 403
    assert (
        client.post(
            unlock_url,
            data={"password": "wrong"},
            content_type="application/json",
        ).status_code
        == 403
    )
    private_process.refresh_from_db()
    assert private_process.view_count == 0

    assert (
        client.post(
            unlock_url,
            data={"password": "process-secret"},
            content_type="application/json",
        ).status_code
        == 204
    )
    response = client.get(detail_url)

    assert response.status_code == 200
    assert response.json()["title"] == "Private process"
    private_process.refresh_from_db()
    assert private_process.view_count == 1


@pytest.mark.django_db
def test_form_grant_does_not_unlock_process_with_same_public_id(
    client,
    user,
    process_form,
):
    shared_id = uuid4()
    form = Form.objects.create(
        public_id=shared_id,
        owner=user,
        title="Private form",
        visibility=Form.Visibility.PRIVATE,
        access_password_hash=make_password("form-secret"),
        status=Form.Status.PUBLISHED,
    )
    Question.objects.create(
        form=form,
        text="Question",
        question_type=Question.QuestionType.TEXT,
        order=1,
    )
    process = Process.objects.create(
        public_id=shared_id,
        owner=user,
        title="Private process",
        process_type=Process.ProcessType.LINEAR,
        visibility=Process.Visibility.PRIVATE,
        access_password_hash=make_password("process-secret"),
        status=Process.Status.PUBLISHED,
    )
    ProcessStep.objects.create(process=process, form=process_form, order=1)

    form_unlock = f"/api/v1/public/forms/{shared_id}/unlock/"
    process_detail = f"/api/v1/public/processes/{shared_id}/"

    assert (
        client.post(
            form_unlock,
            data={"password": "form-secret"},
            content_type="application/json",
        ).status_code
        == 204
    )
    assert client.get(process_detail).status_code == 403


@pytest.mark.django_db
def test_process_read_model_cache_hit_invalidation_and_order(public_process, process_form):
    cache.clear()
    second_form = Form.objects.create(
        owner=public_process.owner,
        title="Second form",
        status=Form.Status.PUBLISHED,
    )
    ProcessStep.objects.create(process=public_process, form=second_form, order=2)

    first = get_process_participant_read_model(process=public_process)
    assert [step["order"] for step in first["steps"]] == [1, 2]

    Process.objects.filter(pk=public_process.pk).update(title="Changed behind cache")
    public_process.refresh_from_db()
    assert get_process_participant_read_model(process=public_process)["title"] == "Public process"

    invalidate_participant_read_model(
        resource_type="process",
        public_id=public_process.public_id,
    )
    assert (
        get_process_participant_read_model(process=public_process)["title"]
        == "Changed behind cache"
    )


@pytest.mark.django_db
def test_process_cache_outage_falls_back_to_database(public_process):
    with (
        patch("apps.core.participant_access.cache.get", side_effect=RuntimeError("down")),
        patch("apps.core.participant_access.cache.set", side_effect=RuntimeError("down")),
    ):
        model = get_process_participant_read_model(process=public_process)

    assert model["title"] == "Public process"


@pytest.mark.django_db
def test_process_close_invalidates_cache(
    public_process,
    user,
    django_capture_on_commit_callbacks,
):
    cache.clear()
    get_process_participant_read_model(process=public_process)

    with django_capture_on_commit_callbacks(execute=True):
        close_process(process=public_process, owner=user)

    public_process.refresh_from_db()
    assert public_process.status == Process.Status.CLOSED

    from apps.core.participant_access import participant_cache_key

    assert (
        cache.get(
            participant_cache_key(
                resource_type="process",
                public_id=public_process.public_id,
            )
        )
        is None
    )


@pytest.mark.django_db
@override_settings(PARTICIPANT_UNLOCK_RATE_LIMIT_COUNT=2)
def test_private_process_html_unlock_rate_limit_stops_password_hashing(
    client,
    private_process,
):
    cache.clear()
    unlock_url = reverse(
        "processes_participant:unlock",
        args=[private_process.public_id],
    )

    with patch(
        "apps.processes.participant_views.verify_participant_password",
        return_value=False,
    ) as verifier:
        first = client.post(
            unlock_url,
            {"password": "wrong-1"},
            REMOTE_ADDR="203.0.113.20",
        )
        second = client.post(
            unlock_url,
            {"password": "wrong-2"},
            REMOTE_ADDR="203.0.113.20",
        )
        blocked = client.post(
            unlock_url,
            {"password": "wrong-3"},
            REMOTE_ADDR="203.0.113.20",
        )

    assert first.status_code == 403
    assert second.status_code == 429
    assert blocked.status_code == 429
    assert blocked["Retry-After"] == "900"
    assert verifier.call_count == 2


@pytest.mark.django_db
@override_settings(PARTICIPANT_UNLOCK_RATE_LIMIT_COUNT=2)
def test_private_process_rest_unlock_rate_limit_stops_password_hashing(
    client,
    private_process,
):
    cache.clear()
    unlock_url = f"/api/v1/public/processes/{private_process.public_id}/unlock/"

    with patch(
        "apps.processes.participant_api_views.verify_participant_password",
        return_value=False,
    ) as verifier:
        first = client.post(
            unlock_url,
            data={"password": "wrong-1"},
            content_type="application/json",
            REMOTE_ADDR="203.0.113.21",
        )
        second = client.post(
            unlock_url,
            data={"password": "wrong-2"},
            content_type="application/json",
            REMOTE_ADDR="203.0.113.21",
        )
        blocked = client.post(
            unlock_url,
            data={"password": "wrong-3"},
            content_type="application/json",
            REMOTE_ADDR="203.0.113.21",
        )

    assert first.status_code == 403
    assert second.status_code == 429
    assert blocked.status_code == 429
    assert blocked.json()["error_code"] == "PARTICIPANT_ACCESS_RATE_LIMITED"
    assert blocked["Retry-After"] == "900"
    assert verifier.call_count == 2



@pytest.mark.django_db
@pytest.mark.parametrize("cache_failure", ["read", "write"])
@pytest.mark.parametrize("surface", ["html", "rest"])
def test_private_process_unlock_fails_closed_across_fresh_sessions_when_redis_is_down(
    private_process,
    cache_failure,
    surface,
):
    cache.clear()
    html_url = reverse("processes_participant:unlock", args=[private_process.public_id])
    api_url = f"/api/v1/public/processes/{private_process.public_id}/unlock/"

    with ExitStack() as stack:
        if cache_failure == "read":
            stack.enter_context(
                patch(
                    "apps.core.participant_access.cache.get",
                    side_effect=RuntimeError("down"),
                )
            )
        else:
            stack.enter_context(
                patch("apps.core.participant_access.cache.get", return_value=None)
            )
            stack.enter_context(
                patch(
                    "apps.core.participant_access.cache.add",
                    side_effect=RuntimeError("down"),
                )
            )

        html_verifier = stack.enter_context(
            patch("apps.processes.participant_views.verify_participant_password")
        )
        api_verifier = stack.enter_context(
            patch("apps.processes.participant_api_views.verify_participant_password")
        )

        for _ in range(3):
            fresh_client = Client()
            if surface == "html":
                response = fresh_client.post(
                    html_url,
                    {"password": "wrong"},
                    REMOTE_ADDR="203.0.113.90",
                )
            else:
                response = fresh_client.post(
                    api_url,
                    data={"password": "wrong"},
                    content_type="application/json",
                    REMOTE_ADDR="203.0.113.90",
                )

            assert response.status_code == 503
            if surface == "rest":
                assert (
                    response.json()["error_code"]
                    == "PARTICIPANT_ACCESS_TEMPORARILY_UNAVAILABLE"
                )

    assert html_verifier.call_count == 0
    assert api_verifier.call_count == 0
