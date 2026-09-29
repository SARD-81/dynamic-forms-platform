from contextlib import ExitStack
from unittest.mock import patch

import pytest
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import reverse

from apps.core.participant_access import invalidate_participant_read_model
from apps.forms.models import Form, Question, QuestionOption
from apps.forms.participant_selectors import get_form_participant_read_model
from apps.forms.services import close_form


@pytest.fixture
def public_form(user):
    form = Form.objects.create(
        owner=user,
        title="Public survey",
        description="Published participant form",
        visibility=Form.Visibility.PUBLIC,
        status=Form.Status.PUBLISHED,
    )
    Question.objects.create(
        form=form,
        text="Your name",
        question_type=Question.QuestionType.TEXT,
        order=1,
        is_required=True,
        max_length=80,
    )
    choice = Question.objects.create(
        form=form,
        text="Pick one",
        question_type=Question.QuestionType.SELECT,
        order=2,
    )
    QuestionOption.objects.create(question=choice, label="Second", order=2)
    QuestionOption.objects.create(question=choice, label="First", order=1)
    return form


@pytest.fixture
def private_form(user):
    form = Form.objects.create(
        owner=user,
        title="Private survey",
        visibility=Form.Visibility.PRIVATE,
        access_password_hash=make_password("form-secret"),
        status=Form.Status.PUBLISHED,
    )
    Question.objects.create(
        form=form,
        text="Private question",
        question_type=Question.QuestionType.TEXT,
        order=1,
    )
    return form


@pytest.mark.django_db
def test_public_form_unique_link_is_anonymous_and_counts_successful_views(client, public_form):
    url = reverse("forms_participant:detail", args=[public_form.public_id])

    first = client.get(url)
    second = client.get(url)

    assert first.status_code == 200
    assert second.status_code == 200
    assert "Public survey" in first.content.decode()
    public_form.refresh_from_db()
    assert public_form.view_count == 2

    head = client.head(url)
    rejected_post = client.post(url)
    public_form.refresh_from_db()

    assert head.status_code == 200
    assert rejected_post.status_code == 405

    api_head = client.head(f"/api/v1/public/forms/{public_form.public_id}/")
    public_form.refresh_from_db()

    assert api_head.status_code == 200
    assert public_form.view_count == 2


@pytest.mark.django_db
def test_form_public_ids_produce_distinct_participant_links(user):
    first = Form.objects.create(owner=user, title="One")
    second = Form.objects.create(owner=user, title="Two")

    assert reverse("forms_participant:detail", args=[first.public_id]) != reverse(
        "forms_participant:detail",
        args=[second.public_id],
    )


@pytest.mark.django_db
@pytest.mark.parametrize("resource_status", [Form.Status.DRAFT, Form.Status.CLOSED])
def test_non_published_form_is_not_participant_accessible(client, user, resource_status):
    form = Form.objects.create(
        owner=user,
        title="Unavailable",
        status=resource_status,
    )

    html = client.get(reverse("forms_participant:detail", args=[form.public_id]))
    api = client.get(f"/api/v1/public/forms/{form.public_id}/")

    assert html.status_code == 404
    assert api.status_code == 404
    form.refresh_from_db()
    assert form.view_count == 0


@pytest.mark.django_db
def test_private_form_requires_password_and_rejected_access_does_not_count(
    client,
    private_form,
):
    detail_url = reverse("forms_participant:detail", args=[private_form.public_id])
    unlock_url = reverse("forms_participant:unlock", args=[private_form.public_id])

    blocked = client.get(detail_url)
    wrong = client.post(unlock_url, {"password": "wrong"})

    assert blocked.status_code == 403
    assert wrong.status_code == 403
    assert "Private survey" not in blocked.content.decode()
    private_form.refresh_from_db()
    assert private_form.view_count == 0

    unlocked = client.post(unlock_url, {"password": "form-secret"})
    assert unlocked.status_code == 302

    allowed = client.get(detail_url)
    assert allowed.status_code == 200
    assert "Private survey" in allowed.content.decode()
    private_form.refresh_from_db()
    assert private_form.view_count == 1


@pytest.mark.django_db
def test_private_form_rest_unlock_uses_session_grant(client, private_form):
    detail_url = f"/api/v1/public/forms/{private_form.public_id}/"
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
    assert (
        client.post(
            unlock_url,
            data={"password": "form-secret"},
            content_type="application/json",
        ).status_code
        == 204
    )

    response = client.get(detail_url)

    assert response.status_code == 200
    assert response.json()["title"] == "Private survey"
    private_form.refresh_from_db()
    assert private_form.view_count == 1


@pytest.mark.django_db
def test_form_participant_read_model_cache_hit_and_explicit_invalidation(public_form):
    cache.clear()

    first = get_form_participant_read_model(form=public_form)
    Form.objects.filter(pk=public_form.pk).update(title="Changed behind cache")
    public_form.refresh_from_db()

    cached = get_form_participant_read_model(form=public_form)
    assert cached["title"] == first["title"] == "Public survey"
    assert [item["label"] for item in cached["questions"][1]["options"]] == [
        "First",
        "Second",
    ]

    invalidate_participant_read_model(resource_type="form", public_id=public_form.public_id)
    refreshed = get_form_participant_read_model(form=public_form)
    assert refreshed["title"] == "Changed behind cache"


@pytest.mark.django_db
def test_form_participant_cache_outage_falls_back_to_database(public_form):
    with (
        patch("apps.core.participant_access.cache.get", side_effect=RuntimeError("down")),
        patch("apps.core.participant_access.cache.set", side_effect=RuntimeError("down")),
    ):
        model = get_form_participant_read_model(form=public_form)

    assert model["title"] == "Public survey"


@pytest.mark.django_db
def test_form_close_invalidates_participant_cache(
    public_form,
    user,
    django_capture_on_commit_callbacks,
):
    cache.clear()
    get_form_participant_read_model(form=public_form)

    with django_capture_on_commit_callbacks(execute=True):
        close_form(
            form=public_form,
            owner=user,
            active_run_checker=lambda **kwargs: False,
        )

    public_form.refresh_from_db()
    assert public_form.status == Form.Status.CLOSED
    assert client_cache_miss_for_form(public_form)


def client_cache_miss_for_form(form):
    from apps.core.participant_access import participant_cache_key

    return cache.get(participant_cache_key(resource_type="form", public_id=form.public_id)) is None


@pytest.mark.django_db
def test_owner_management_endpoint_remains_separate_from_participant_access(
    client,
    public_form,
):
    participant = client.get(reverse("forms_participant:detail", args=[public_form.public_id]))
    owner_manage = client.get(reverse("forms:detail", args=[public_form.id]))

    assert participant.status_code == 200
    assert owner_manage.status_code == 302


@pytest.mark.django_db
@override_settings(PARTICIPANT_UNLOCK_RATE_LIMIT_COUNT=2)
def test_private_form_html_unlock_rate_limit_stops_password_hashing(client, private_form):
    cache.clear()
    unlock_url = reverse("forms_participant:unlock", args=[private_form.public_id])

    with patch(
        "apps.forms.participant_views.verify_participant_password",
        return_value=False,
    ) as verifier:
        first = client.post(
            unlock_url,
            {"password": "wrong-1"},
            REMOTE_ADDR="203.0.113.10",
        )
        second = client.post(
            unlock_url,
            {"password": "wrong-2"},
            REMOTE_ADDR="203.0.113.10",
        )
        blocked = client.post(
            unlock_url,
            {"password": "wrong-3"},
            REMOTE_ADDR="203.0.113.10",
        )

    assert first.status_code == 403
    assert second.status_code == 403
    assert blocked.status_code == 429
    assert blocked["Retry-After"] == "900"
    assert verifier.call_count == 2


@pytest.mark.django_db
@override_settings(PARTICIPANT_UNLOCK_RATE_LIMIT_COUNT=2)
def test_private_form_rest_unlock_rate_limit_stops_password_hashing(client, private_form):
    cache.clear()
    unlock_url = f"/api/v1/public/forms/{private_form.public_id}/unlock/"

    with patch(
        "apps.forms.participant_api_views.verify_participant_password",
        return_value=False,
    ) as verifier:
        first = client.post(
            unlock_url,
            data={"password": "wrong-1"},
            content_type="application/json",
            REMOTE_ADDR="203.0.113.11",
        )
        second = client.post(
            unlock_url,
            data={"password": "wrong-2"},
            content_type="application/json",
            REMOTE_ADDR="203.0.113.11",
        )
        blocked = client.post(
            unlock_url,
            data={"password": "wrong-3"},
            content_type="application/json",
            REMOTE_ADDR="203.0.113.11",
        )

    assert first.status_code == 403
    assert second.status_code == 403
    assert blocked.status_code == 429
    assert blocked.json()["error_code"] == "PARTICIPANT_ACCESS_RATE_LIMITED"
    assert blocked["Retry-After"] == "900"
    assert verifier.call_count == 2


@pytest.mark.django_db
@pytest.mark.parametrize("cache_failure", ["read", "write"])
@pytest.mark.parametrize("surface", ["html", "rest"])
def test_private_form_unlock_fails_closed_across_fresh_sessions_when_redis_is_down(
    private_form,
    cache_failure,
    surface,
):
    cache.clear()
    html_url = reverse("forms_participant:unlock", args=[private_form.public_id])
    api_url = f"/api/v1/public/forms/{private_form.public_id}/unlock/"

    with ExitStack() as stack:
        if cache_failure == "read":
            stack.enter_context(
                patch(
                    "apps.core.participant_access.cache.get",
                    side_effect=RuntimeError("down"),
                )
            )
        else:
            stack.enter_context(patch("apps.core.participant_access.cache.get", return_value=None))
            stack.enter_context(
                patch(
                    "apps.core.participant_access.cache.add",
                    side_effect=RuntimeError("down"),
                )
            )

        html_verifier = stack.enter_context(
            patch("apps.forms.participant_views.verify_participant_password")
        )
        api_verifier = stack.enter_context(
            patch("apps.forms.participant_api_views.verify_participant_password")
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
                assert response.json()["error_code"] == "PARTICIPANT_ACCESS_TEMPORARILY_UNAVAILABLE"

    assert html_verifier.call_count == 0
    assert api_verifier.call_count == 0
