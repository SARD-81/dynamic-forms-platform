import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.forms.models import Form


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="form-view-other",
        email="form-view-other@example.com",
        password="test-password",
    )


def test_form_list_requires_login(client):
    response = client.get(reverse("forms:list"))

    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


@pytest.mark.django_db
def test_form_list_only_shows_current_users_forms(client, user, other_user):
    Form.objects.create(owner=user, title="Visible form")
    Form.objects.create(owner=other_user, title="Hidden form")
    client.force_login(user)

    response = client.get(reverse("forms:list"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Visible form" in content
    assert "Hidden form" not in content


@pytest.mark.django_db
def test_create_and_edit_draft_form(client, user):
    client.force_login(user)

    create_response = client.post(
        reverse("forms:create"),
        {
            "title": "First title",
            "description": "First description",
            "category": "",
            "visibility": Form.Visibility.PUBLIC,
            "access_password": "",
        },
    )

    form = Form.objects.get(owner=user)
    assert create_response.status_code == 302
    assert form.status == Form.Status.DRAFT

    update_response = client.post(
        reverse("forms:update", args=[form.id]),
        {
            "title": "Updated title",
            "description": "Updated description",
            "category": "",
            "visibility": Form.Visibility.PUBLIC,
            "access_password": "",
        },
    )

    form.refresh_from_db()
    assert update_response.status_code == 302
    assert form.title == "Updated title"


@pytest.mark.django_db
def test_cross_user_form_detail_returns_404(client, user, other_user):
    form = Form.objects.create(owner=other_user, title="Hidden")
    client.force_login(user)

    response = client.get(reverse("forms:detail", args=[form.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_published_form_cannot_be_edited_or_deleted(client, user):
    form = Form.objects.create(
        owner=user,
        title="Published",
        status=Form.Status.PUBLISHED,
    )
    client.force_login(user)

    update_response = client.post(
        reverse("forms:update", args=[form.id]),
        {
            "title": "Changed",
            "description": "",
            "category": "",
            "visibility": Form.Visibility.PUBLIC,
            "access_password": "",
        },
    )
    delete_response = client.post(reverse("forms:delete", args=[form.id]))

    form.refresh_from_db()
    assert update_response.status_code == 302
    assert delete_response.status_code == 302
    assert form.title == "Published"
    assert Form.objects.filter(pk=form.pk).exists()


@pytest.mark.django_db
def test_publish_and_close_html_flow(client, user):
    form = Form.objects.create(owner=user, title="Lifecycle")
    client.force_login(user)

    publish_response = client.post(reverse("forms:publish", args=[form.id]))
    form.refresh_from_db()

    assert publish_response.status_code == 302
    assert form.status == Form.Status.PUBLISHED

    close_response = client.post(reverse("forms:close", args=[form.id]))
    form.refresh_from_db()

    assert close_response.status_code == 302
    assert form.status == Form.Status.CLOSED
