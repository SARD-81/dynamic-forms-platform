import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.core.models import Category
from apps.core.services import create_category, delete_category, rename_category
from apps.forms.models import Form
from apps.processes.models import Process


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="other-user",
        email="other-user@example.com",
        password="test-password",
    )


@pytest.mark.django_db
def test_create_category_trims_name_and_assigns_owner(user):
    category = create_category(owner=user, name="  Work  ")

    assert category.owner == user
    assert category.name == "Work"


@pytest.mark.django_db
def test_create_category_rejects_blank_name(user):
    with pytest.raises(ValidationError):
        create_category(owner=user, name="   ")


@pytest.mark.django_db
def test_duplicate_category_name_is_rejected_for_same_owner(user):
    create_category(owner=user, name="Shared")

    with pytest.raises(ValidationError):
        create_category(owner=user, name="Shared")


@pytest.mark.django_db
def test_same_category_name_is_allowed_for_different_owners(user, other_user):
    first = create_category(owner=user, name="Shared")
    second = create_category(owner=other_user, name="Shared")

    assert first.owner != second.owner


@pytest.mark.django_db
def test_rename_category_rejects_cross_owner_write(user, other_user):
    category = create_category(owner=other_user, name="Private")

    with pytest.raises(PermissionDenied):
        rename_category(category=category, owner=user, name="Changed")

    category.refresh_from_db()
    assert category.name == "Private"


@pytest.mark.django_db
def test_delete_category_rejects_cross_owner_write(user, other_user):
    category = create_category(owner=other_user, name="Private")

    with pytest.raises(PermissionDenied):
        delete_category(category=category, owner=user)

    assert Category.objects.filter(pk=category.pk).exists()


@pytest.mark.django_db
def test_delete_category_keeps_related_forms_and_processes(user):
    category = create_category(owner=user, name="Projects")
    form = Form.objects.create(owner=user, category=category, title="Survey")
    process = Process.objects.create(
        owner=user,
        category=category,
        title="Onboarding",
        process_type=Process.ProcessType.LINEAR,
    )

    delete_category(category=category, owner=user)

    form.refresh_from_db()
    process.refresh_from_db()

    assert not Category.objects.filter(pk=category.pk).exists()
    assert Form.objects.filter(pk=form.pk).exists()
    assert Process.objects.filter(pk=process.pk).exists()
    assert form.category_id is None
    assert process.category_id is None
