import json

import pytest

from apps.accounts.models import User
from apps.forms.models import Form, Question
from apps.forms.services import create_question, create_question_option, publish_form

QUESTION_TYPE = Question.QuestionType


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="builder-api-other",
        email="builder-api-other@example.com",
        password="test-password",
    )


@pytest.fixture
def draft_form(user):
    return Form.objects.create(owner=user, title="API builder")


@pytest.mark.django_db
def test_question_api_crud_and_nested_options(client, user, draft_form):
    client.force_login(user)
    list_url = f"/api/v1/forms/{draft_form.id}/questions/"

    create_response = client.post(
        list_url,
        data=json.dumps(
            {
                "text": "Pick one",
                "question_type": QUESTION_TYPE.SELECT,
                "is_required": True,
            }
        ),
        content_type="application/json",
    )

    assert create_response.status_code == 201
    question_id = create_response.json()["id"]
    option_url = f"{list_url}{question_id}/options/"

    option_response = client.post(
        option_url,
        data=json.dumps({"label": "Alpha"}),
        content_type="application/json",
    )
    assert option_response.status_code == 201

    detail_response = client.get(f"{list_url}{question_id}/")
    assert detail_response.status_code == 200
    assert detail_response.json()["options"][0]["label"] == "Alpha"

    patch_response = client.patch(
        f"{list_url}{question_id}/",
        data=json.dumps({"text": "Pick exactly one"}),
        content_type="application/json",
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["text"] == "Pick exactly one"


@pytest.mark.django_db
def test_question_and_option_api_reorder(client, user, draft_form):
    first = create_question(
        form=draft_form,
        owner=user,
        text="First",
        question_type=QUESTION_TYPE.TEXT,
    )
    second = create_question(
        form=draft_form,
        owner=user,
        text="Second",
        question_type=QUESTION_TYPE.SELECT,
    )
    option_one = create_question_option(question=second, owner=user, label="One")
    option_two = create_question_option(question=second, owner=user, label="Two")
    client.force_login(user)

    option_response = client.post(
        f"/api/v1/forms/{draft_form.id}/questions/{second.id}/options/reorder/",
        data=json.dumps({"option_ids": [option_two.id, option_one.id]}),
        content_type="application/json",
    )
    assert option_response.status_code == 200
    assert [item["id"] for item in option_response.json()] == [
        option_two.id,
        option_one.id,
    ]

    question_response = client.post(
        f"/api/v1/forms/{draft_form.id}/questions/reorder/",
        data=json.dumps({"question_ids": [second.id, first.id]}),
        content_type="application/json",
    )
    assert question_response.status_code == 200
    assert [item["id"] for item in question_response.json()] == [second.id, first.id]
    assert [item["id"] for item in question_response.json()[0]["options"]] == [
        option_two.id,
        option_one.id,
    ]


@pytest.mark.django_db
def test_question_api_rejects_max_length_outside_database_range(
    client,
    user,
    draft_form,
):
    client.force_login(user)

    response = client.post(
        f"/api/v1/forms/{draft_form.id}/questions/",
        data=json.dumps(
            {
                "text": "Too large",
                "question_type": QUESTION_TYPE.TEXT,
                "max_length": 2147483648,
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "max_length" in response.json()["field_errors"]


@pytest.mark.django_db
def test_question_api_rejects_invalid_config_and_duplicate_option(
    client,
    user,
    draft_form,
):
    client.force_login(user)
    list_url = f"/api/v1/forms/{draft_form.id}/questions/"

    invalid = client.post(
        list_url,
        data=json.dumps(
            {
                "text": "Invalid",
                "question_type": QUESTION_TYPE.TEXT,
                "min_value": "1",
            }
        ),
        content_type="application/json",
    )
    assert invalid.status_code == 400
    assert "configuration" in invalid.json()["field_errors"]

    question = create_question(
        form=draft_form,
        owner=user,
        text="Choice",
        question_type=QUESTION_TYPE.SELECT,
    )
    option_url = f"{list_url}{question.id}/options/"
    assert (
        client.post(
            option_url,
            data=json.dumps({"label": "One"}),
            content_type="application/json",
        ).status_code
        == 201
    )
    duplicate = client.post(
        option_url,
        data=json.dumps({"label": " One "}),
        content_type="application/json",
    )
    assert duplicate.status_code == 400
    assert "label" in duplicate.json()["field_errors"]


@pytest.mark.django_db
def test_question_api_hides_other_users_schema(client, user, other_user):
    foreign_form = Form.objects.create(owner=other_user, title="Foreign")
    foreign_question = Question.objects.create(
        form=foreign_form,
        text="Hidden",
        question_type=QUESTION_TYPE.TEXT,
        order=1,
    )
    client.force_login(user)

    assert client.get(f"/api/v1/forms/{foreign_form.id}/questions/").status_code == 404
    assert (
        client.get(f"/api/v1/forms/{foreign_form.id}/questions/{foreign_question.id}/").status_code
        == 404
    )


@pytest.mark.django_db
def test_question_api_rejects_mutation_after_publish(client, user, draft_form):
    question = create_question(
        form=draft_form,
        owner=user,
        text="Choice",
        question_type=QUESTION_TYPE.SELECT,
    )
    option = create_question_option(question=question, owner=user, label="One")
    publish_form(form=draft_form, owner=user)
    client.force_login(user)

    question_url = f"/api/v1/forms/{draft_form.id}/questions/{question.id}/"
    option_url = f"{question_url}options/{option.id}/"

    assert (
        client.patch(
            question_url,
            data=json.dumps({"text": "Changed"}),
            content_type="application/json",
        ).status_code
        == 400
    )
    assert client.delete(question_url).status_code == 400
    assert (
        client.post(
            f"/api/v1/forms/{draft_form.id}/questions/",
            data=json.dumps(
                {
                    "text": "Late",
                    "question_type": QUESTION_TYPE.TEXT,
                }
            ),
            content_type="application/json",
        ).status_code
        == 400
    )
    assert (
        client.patch(
            option_url,
            data=json.dumps({"label": "Changed"}),
            content_type="application/json",
        ).status_code
        == 400
    )


@pytest.mark.django_db
def test_question_builder_openapi_declares_list_responses_as_arrays(client, user):
    client.force_login(user)

    response = client.get("/api/schema/", {"format": "json"})

    assert response.status_code == 200
    schema = response.json()
    question_schema = schema["paths"]["/api/v1/forms/{form_id}/questions/"]["get"]["responses"][
        "200"
    ]["content"]["application/json"]["schema"]
    option_schema = schema["paths"]["/api/v1/forms/{form_id}/questions/{question_id}/options/"][
        "get"
    ]["responses"]["200"]["content"]["application/json"]["schema"]

    assert question_schema["type"] == "array"
    assert question_schema["items"]["$ref"] == "#/components/schemas/Question"
    assert option_schema["type"] == "array"
    assert option_schema["items"]["$ref"] == "#/components/schemas/QuestionOption"
