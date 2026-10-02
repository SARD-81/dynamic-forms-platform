import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.core.models import Category


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="view-other",
        email="view-other@example.com",
        password="test-password",
    )


def test_category_list_requires_login(client):
    response = client.get(reverse("core:category_list"))

    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


@pytest.mark.django_db
def test_category_list_only_shows_current_users_categories(client, user, other_user):
    own = Category.objects.create(owner=user, name="My category")
    Category.objects.create(owner=other_user, name="Someone else's category")
    client.force_login(user)

    response = client.get(reverse("core:category_list"))
    content = response.content.decode()

    assert response.status_code == 200
    assert own.name in content
    assert "Someone else's category" not in content


@pytest.mark.django_db
def test_category_create_happy_path(client, user):
    client.force_login(user)

    response = client.post(
        reverse("core:category_create"),
        {"name": "  University  "},
    )

    assert response.status_code == 302
    assert response.url == reverse("core:category_list")
    assert Category.objects.filter(owner=user, name="University").exists()


@pytest.mark.django_db
def test_category_create_duplicate_is_rendered_as_validation_error(client, user):
    Category.objects.create(owner=user, name="Shared")
    client.force_login(user)

    response = client.post(reverse("core:category_create"), {"name": "Shared"})

    assert response.status_code == 200
    assert "You already have a category with this name." in response.content.decode()
    assert Category.objects.filter(owner=user, name="Shared").count() == 1


@pytest.mark.django_db
def test_category_update_happy_path(client, user):
    category = Category.objects.create(owner=user, name="Old")
    client.force_login(user)

    response = client.post(
        reverse("core:category_update", args=[category.id]),
        {"name": "New"},
    )

    category.refresh_from_db()
    assert response.status_code == 302
    assert category.name == "New"


@pytest.mark.django_db
def test_cross_user_category_update_and_delete_return_404(client, user, other_user):
    category = Category.objects.create(owner=other_user, name="Hidden")
    client.force_login(user)

    update_response = client.post(
        reverse("core:category_update", args=[category.id]),
        {"name": "Changed"},
    )
    delete_response = client.post(
        reverse("core:category_delete", args=[category.id]),
    )

    assert update_response.status_code == 404
    assert delete_response.status_code == 404
    category.refresh_from_db()
    assert category.name == "Hidden"


@pytest.mark.django_db
def test_category_delete_happy_path(client, user):
    category = Category.objects.create(owner=user, name="Temporary")
    client.force_login(user)

    response = client.post(reverse("core:category_delete", args=[category.id]))

    assert response.status_code == 302
    assert not Category.objects.filter(pk=category.pk).exists()
