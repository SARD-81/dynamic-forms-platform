import pytest

from apps.accounts.models import User
from apps.core.models import Category
from apps.core.selectors import get_category_choices_for_owner, get_category_for_owner


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="selector-other",
        email="selector-other@example.com",
        password="test-password",
    )


@pytest.mark.django_db
def test_category_choices_are_owner_scoped_and_ordered(user, other_user):
    zeta = Category.objects.create(owner=user, name="Zeta")
    alpha = Category.objects.create(owner=user, name="Alpha")
    Category.objects.create(owner=other_user, name="Hidden")

    categories = list(get_category_choices_for_owner(owner=user))

    assert [category.id for category in categories] == [alpha.id, zeta.id]
    assert [category.name for category in categories] == ["Alpha", "Zeta"]
    assert all(category.owner_id == user.id for category in categories)


@pytest.mark.django_db
def test_get_category_for_owner_hides_other_users_category(user, other_user):
    category = Category.objects.create(owner=other_user, name="Hidden")

    assert get_category_for_owner(owner=user, category_id=category.id) is None
    assert get_category_for_owner(owner=other_user, category_id=category.id) == category
