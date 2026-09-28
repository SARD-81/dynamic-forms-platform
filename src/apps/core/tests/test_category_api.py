import json

import pytest

from apps.accounts.models import User
from apps.core.models import Category

CATEGORY_LIST_URL = "/api/v1/categories/"


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="api-other",
        email="api-other@example.com",
        password="test-password",
    )


def test_category_api_requires_authentication(client):
    response = client.get(CATEGORY_LIST_URL)

    assert response.status_code == 403


@pytest.mark.django_db
def test_category_api_list_is_owner_scoped(client, user, other_user):
    Category.objects.create(owner=user, name="Visible")
    Category.objects.create(owner=other_user, name="Hidden")
    client.force_login(user)

    response = client.get(CATEGORY_LIST_URL)

    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Visible"]


@pytest.mark.django_db
def test_category_api_create_assigns_authenticated_owner(client, user):
    client.force_login(user)

    response = client.post(
        CATEGORY_LIST_URL,
        data=json.dumps({"name": "API category"}),
        content_type="application/json",
    )

    assert response.status_code == 201
    category = Category.objects.get(pk=response.json()["id"])
    assert category.owner == user
    assert category.name == "API category"


@pytest.mark.django_db
def test_category_api_rejects_duplicate_for_same_owner(client, user):
    Category.objects.create(owner=user, name="Shared")
    client.force_login(user)

    response = client.post(
        CATEGORY_LIST_URL,
        data=json.dumps({"name": "Shared"}),
        content_type="application/json",
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "CATEGORY_VALIDATION_ERROR"
    assert "name" in payload["field_errors"]


@pytest.mark.django_db
def test_category_api_patch_renames_category(client, user):
    category = Category.objects.create(owner=user, name="Old")
    client.force_login(user)

    response = client.patch(
        f"{CATEGORY_LIST_URL}{category.id}/",
        data=json.dumps({"name": "New"}),
        content_type="application/json",
    )

    category.refresh_from_db()
    assert response.status_code == 200
    assert response.json()["name"] == "New"
    assert category.name == "New"


@pytest.mark.django_db
def test_category_api_cross_user_access_returns_404(client, user, other_user):
    category = Category.objects.create(owner=other_user, name="Hidden")
    client.force_login(user)
    detail_url = f"{CATEGORY_LIST_URL}{category.id}/"

    assert client.get(detail_url).status_code == 404
    assert (
        client.patch(
            detail_url,
            data=json.dumps({"name": "Changed"}),
            content_type="application/json",
        ).status_code
        == 404
    )
    assert client.delete(detail_url).status_code == 404


@pytest.mark.django_db
def test_category_api_delete_removes_owned_category(client, user):
    category = Category.objects.create(owner=user, name="Temporary")
    client.force_login(user)

    response = client.delete(f"{CATEGORY_LIST_URL}{category.id}/")

    assert response.status_code == 204
    assert not Category.objects.filter(pk=category.pk).exists()
