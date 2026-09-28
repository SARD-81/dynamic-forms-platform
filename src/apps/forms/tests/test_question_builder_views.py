import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.forms.models import Form, Question
from apps.forms.services import create_question, create_question_option, publish_form


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="builder-view-other",
        email="builder-view-other@example.com",
        password="test-password",
    )


@pytest.fixture
def draft_form(user):
    return Form.objects.create(owner=user, title="HTML builder")


@pytest.mark.django_db
def test_builder_requires_owner_and_lists_questions(client, user, other_user, draft_form):
    question = create_question(
        form=draft_form,
        owner=user,
        text="Visible question",
        question_type=Question.QuestionType.TEXT,
    )
    client.force_login(user)

    response = client.get(reverse("forms:builder", args=[draft_form.id]))

    assert response.status_code == 200
    assert "Visible question" in response.content.decode()
    assert (
        reverse("forms:question_update", args=[draft_form.id, question.id])
        in response.content.decode()
    )

    client.force_login(other_user)
    assert client.get(reverse("forms:builder", args=[draft_form.id])).status_code == 404


@pytest.mark.django_db
def test_html_builder_can_create_question_and_option(client, user, draft_form):
    client.force_login(user)

    question_response = client.post(
        reverse("forms:question_create", args=[draft_form.id]),
        {
            "text": "Pick one",
            "question_type": Question.QuestionType.SELECT,
            "is_required": "on",
            "max_length": "",
            "min_value": "",
            "max_value": "",
        },
    )

    question = Question.objects.get(form=draft_form)
    assert question_response.status_code == 302
    assert question.order == 1

    option_response = client.post(
        reverse("forms:option_create", args=[draft_form.id, question.id]),
        {"label": "Alpha"},
    )

    assert option_response.status_code == 302
    assert question.options.get().label == "Alpha"


@pytest.mark.django_db
def test_html_move_and_delete_reindexes_questions(client, user, draft_form):
    first = create_question(
        form=draft_form,
        owner=user,
        text="First",
        question_type=Question.QuestionType.TEXT,
    )
    second = create_question(
        form=draft_form,
        owner=user,
        text="Second",
        question_type=Question.QuestionType.TEXT,
    )
    client.force_login(user)

    move_response = client.post(
        reverse(
            "forms:question_move",
            args=[draft_form.id, second.id, "up"],
        )
    )
    assert move_response.status_code == 302

    second.refresh_from_db()
    first.refresh_from_db()
    assert second.order == 1
    assert first.order == 2

    delete_response = client.post(reverse("forms:question_delete", args=[draft_form.id, second.id]))
    assert delete_response.status_code == 302

    first.refresh_from_db()
    assert first.order == 1


@pytest.mark.django_db
def test_published_builder_is_read_only_and_mutation_is_blocked(
    client,
    user,
    draft_form,
):
    question = create_question(
        form=draft_form,
        owner=user,
        text="Choice",
        question_type=Question.QuestionType.SELECT,
    )
    create_question_option(question=question, owner=user, label="One")
    publish_form(form=draft_form, owner=user)
    client.force_login(user)

    builder_response = client.get(reverse("forms:builder", args=[draft_form.id]))
    content = builder_response.content.decode()

    assert builder_response.status_code == 200
    assert "schema is immutable" in content
    assert "Add question" not in content

    update_response = client.post(
        reverse("forms:question_update", args=[draft_form.id, question.id]),
        {
            "text": "Changed",
            "question_type": Question.QuestionType.SELECT,
            "max_length": "",
            "min_value": "",
            "max_value": "",
        },
    )
    question.refresh_from_db()

    assert update_response.status_code == 302
    assert question.text == "Choice"
