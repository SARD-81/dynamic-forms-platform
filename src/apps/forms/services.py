from django.contrib.auth.hashers import make_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.core.selectors import get_category_for_owner

from .models import Form

FORM_NOT_DRAFT_MESSAGE = "Only draft forms can be edited or deleted."
FORM_PUBLISH_MESSAGE = "Only draft forms can be published."
FORM_CLOSE_MESSAGE = "Only published forms can be closed."
FORM_ACTIVE_RUN_MESSAGE = "This form cannot be closed while an active process run depends on it."

_UNSET = object()


def _ensure_owner(*, form, owner):
    if form.owner_id != owner.pk:
        raise PermissionDenied("You do not own this form.")


def _clean_title(title):
    title = title.strip()
    if not title:
        raise ValidationError({"title": ["This field is required."]})
    if len(title) > 200:
        raise ValidationError({"title": ["Ensure this value has at most 200 characters."]})
    return title


def _validate_visibility(visibility):
    if visibility not in Form.Visibility.values:
        raise ValidationError({"visibility": ["Select a valid visibility."]})


def _category_for_owner(*, owner, category_id):
    if category_id is None:
        return None

    category = get_category_for_owner(owner=owner, category_id=category_id)
    if category is None:
        raise ValidationError({"category": ["Select a valid category from your workspace."]})
    return category


def _password_hash_for_visibility(
    *,
    visibility,
    access_password,
    existing_form=None,
):
    if visibility == Form.Visibility.PUBLIC:
        return None

    if access_password:
        return make_password(access_password)

    if (
        existing_form is not None
        and existing_form.visibility == Form.Visibility.PRIVATE
        and existing_form.access_password_hash
    ):
        return existing_form.access_password_hash

    raise ValidationError({"access_password": ["A password is required for private forms."]})


def create_form(
    *,
    owner,
    title,
    description="",
    category_id=None,
    visibility=Form.Visibility.PUBLIC,
    access_password=None,
):
    title = _clean_title(title)
    _validate_visibility(visibility)
    category = _category_for_owner(owner=owner, category_id=category_id)
    password_hash = _password_hash_for_visibility(
        visibility=visibility,
        access_password=access_password,
    )

    with transaction.atomic():
        return Form.objects.create(
            owner=owner,
            title=title,
            description=description.strip(),
            category=category,
            visibility=visibility,
            access_password_hash=password_hash,
            status=Form.Status.DRAFT,
        )


def update_draft_form(
    *,
    form,
    owner,
    title=_UNSET,
    description=_UNSET,
    category_id=_UNSET,
    visibility=_UNSET,
    access_password=_UNSET,
):
    with transaction.atomic():
        locked_form = Form.objects.select_for_update().get(pk=form.pk)
        _ensure_owner(form=locked_form, owner=owner)

        if locked_form.status != Form.Status.DRAFT:
            raise ValidationError({"status": [FORM_NOT_DRAFT_MESSAGE]})

        if title is _UNSET:
            title = locked_form.title
        else:
            title = _clean_title(title)

        if description is _UNSET:
            description = locked_form.description
        else:
            description = description.strip()

        if category_id is _UNSET:
            category = locked_form.category
        else:
            category = _category_for_owner(owner=owner, category_id=category_id)

        if visibility is _UNSET:
            visibility = locked_form.visibility
        else:
            _validate_visibility(visibility)

        password_input = None if access_password is _UNSET else access_password
        password_hash = _password_hash_for_visibility(
            visibility=visibility,
            access_password=password_input,
            existing_form=locked_form,
        )

        locked_form.title = title
        locked_form.description = description
        locked_form.category = category
        locked_form.visibility = visibility
        locked_form.access_password_hash = password_hash
        locked_form.save(
            update_fields=[
                "title",
                "description",
                "category",
                "visibility",
                "access_password_hash",
                "updated_at",
            ]
        )

    return locked_form


def publish_form(*, form, owner):
    with transaction.atomic():
        locked_form = Form.objects.select_for_update().get(pk=form.pk)
        _ensure_owner(form=locked_form, owner=owner)

        if locked_form.status != Form.Status.DRAFT:
            raise ValidationError({"status": [FORM_PUBLISH_MESSAGE]})

        locked_form.status = Form.Status.PUBLISHED
        locked_form.save(update_fields=["status", "updated_at"])

    return locked_form


def close_form(*, form, owner, active_run_checker):
    with transaction.atomic():
        locked_form = Form.objects.select_for_update().get(pk=form.pk)
        _ensure_owner(form=locked_form, owner=owner)

        if locked_form.status != Form.Status.PUBLISHED:
            raise ValidationError({"status": [FORM_CLOSE_MESSAGE]})

        if active_run_checker(form_id=locked_form.pk):
            raise ValidationError({"status": [FORM_ACTIVE_RUN_MESSAGE]})

        locked_form.status = Form.Status.CLOSED
        locked_form.save(update_fields=["status", "updated_at"])

    return locked_form


def delete_draft_form(*, form, owner):
    with transaction.atomic():
        locked_form = Form.objects.select_for_update().get(pk=form.pk)
        _ensure_owner(form=locked_form, owner=owner)

        if locked_form.status != Form.Status.DRAFT:
            raise ValidationError({"status": [FORM_NOT_DRAFT_MESSAGE]})

        locked_form.delete()
