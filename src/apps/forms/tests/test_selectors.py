import pytest

from apps.accounts.models import User
from apps.forms.models import Form
from apps.forms.selectors import get_form_for_owner, get_forms_for_owner


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="form-selector-other",
        email="form-selector-other@example.com",
        password="test-password",
    )


@pytest.mark.django_db
def test_form_selectors_are_owner_scoped(user, other_user):
    visible = Form.objects.create(owner=user, title="Visible")
    Form.objects.create(owner=other_user, title="Hidden")

    forms = list(get_forms_for_owner(owner=user))

    assert [form.id for form in forms] == [visible.id]
    assert get_form_for_owner(owner=user, form_id=visible.id) == visible


@pytest.mark.django_db
def test_get_form_for_owner_hides_other_users_form(user, other_user):
    form = Form.objects.create(owner=other_user, title="Hidden")

    assert get_form_for_owner(owner=user, form_id=form.id) is None
