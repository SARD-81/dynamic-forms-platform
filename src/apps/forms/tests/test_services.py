import pytest
from django.contrib.auth.hashers import check_password
from django.core.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.core.models import Category
from apps.forms.models import Form
from apps.forms.services import (
    close_form,
    create_form,
    delete_draft_form,
    publish_form,
    update_draft_form,
)


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="form-service-other",
        email="form-service-other@example.com",
        password="test-password",
    )


@pytest.mark.django_db
def test_create_public_form_has_no_password_hash(user):
    form = create_form(owner=user, title="Public form")

    assert form.status == Form.Status.DRAFT
    assert form.visibility == Form.Visibility.PUBLIC
    assert form.access_password_hash is None


@pytest.mark.django_db
def test_create_private_form_hashes_password(user):
    form = create_form(
        owner=user,
        title="Private form",
        visibility=Form.Visibility.PRIVATE,
        access_password="secret-pass",
    )

    assert form.access_password_hash != "secret-pass"
    assert check_password("secret-pass", form.access_password_hash)


@pytest.mark.django_db
def test_private_form_requires_password(user):
    with pytest.raises(ValidationError):
        create_form(
            owner=user,
            title="Private form",
            visibility=Form.Visibility.PRIVATE,
        )


@pytest.mark.django_db
def test_form_category_must_belong_to_owner(user, other_user):
    category = Category.objects.create(owner=other_user, name="Hidden")

    with pytest.raises(ValidationError):
        create_form(owner=user, title="Draft", category_id=category.id)


@pytest.mark.django_db
def test_update_draft_form_can_change_definition(user):
    category = Category.objects.create(owner=user, name="Work")
    form = create_form(owner=user, title="Old")

    updated = update_draft_form(
        form=form,
        owner=user,
        title="New",
        description="Updated description",
        category_id=category.id,
        visibility=Form.Visibility.PRIVATE,
        access_password="new-secret",
    )

    assert updated.title == "New"
    assert updated.description == "Updated description"
    assert updated.category == category
    assert updated.visibility == Form.Visibility.PRIVATE
    assert check_password("new-secret", updated.access_password_hash)


@pytest.mark.django_db
def test_private_draft_edit_keeps_existing_password_when_blank(user):
    form = create_form(
        owner=user,
        title="Private",
        visibility=Form.Visibility.PRIVATE,
        access_password="secret-pass",
    )
    original_hash = form.access_password_hash

    updated = update_draft_form(
        form=form,
        owner=user,
        title="Private renamed",
        description="",
        category_id=None,
        visibility=Form.Visibility.PRIVATE,
        access_password=None,
    )

    assert updated.access_password_hash == original_hash


@pytest.mark.django_db
def test_published_form_definition_is_immutable(user):
    form = create_form(owner=user, title="Draft")
    published = publish_form(form=form, owner=user)

    with pytest.raises(ValidationError):
        update_draft_form(
            form=published,
            owner=user,
            title="Changed",
            description="",
            category_id=None,
            visibility=Form.Visibility.PUBLIC,
        )

    published.refresh_from_db()
    assert published.title == "Draft"


@pytest.mark.django_db
def test_lifecycle_only_allows_draft_to_published_to_closed(user):
    form = create_form(owner=user, title="Lifecycle")

    with pytest.raises(ValidationError):
        close_form(
            form=form,
            owner=user,
            active_run_checker=lambda **kwargs: False,
        )

    published = publish_form(form=form, owner=user)

    with pytest.raises(ValidationError):
        publish_form(form=published, owner=user)

    closed = close_form(
        form=published,
        owner=user,
        active_run_checker=lambda **kwargs: False,
    )

    assert closed.status == Form.Status.CLOSED

    with pytest.raises(ValidationError):
        publish_form(form=closed, owner=user)

    with pytest.raises(ValidationError):
        close_form(
            form=closed,
            owner=user,
            active_run_checker=lambda **kwargs: False,
        )


@pytest.mark.django_db
def test_close_is_blocked_when_active_process_run_depends_on_form(user):
    form = create_form(owner=user, title="Published")
    form = publish_form(form=form, owner=user)

    with pytest.raises(ValidationError):
        close_form(
            form=form,
            owner=user,
            active_run_checker=lambda **kwargs: True,
        )

    form.refresh_from_db()
    assert form.status == Form.Status.PUBLISHED


@pytest.mark.django_db
def test_only_draft_form_can_be_hard_deleted(user):
    draft = create_form(owner=user, title="Delete me")
    draft_id = draft.id
    delete_draft_form(form=draft, owner=user)
    assert not Form.objects.filter(pk=draft_id).exists()

    published = create_form(owner=user, title="Keep me")
    published = publish_form(form=published, owner=user)

    with pytest.raises(ValidationError):
        delete_draft_form(form=published, owner=user)

    assert Form.objects.filter(pk=published.pk).exists()


@pytest.mark.django_db
def test_service_rejects_cross_owner_management(user, other_user):
    form = create_form(owner=other_user, title="Other owner's form")

    with pytest.raises(PermissionDenied):
        publish_form(form=form, owner=user)
