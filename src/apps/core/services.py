from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from .models import Category

DUPLICATE_CATEGORY_MESSAGE = "You already have a category with this name."


def _clean_category_name(name):
    name = name.strip()
    if not name:
        raise ValidationError({"name": ["This field is required."]})
    if len(name) > 120:
        raise ValidationError({"name": ["Ensure this value has at most 120 characters."]})
    return name


def _ensure_owner(*, category, owner):
    if category.owner_id != owner.pk:
        raise PermissionDenied("You do not own this category.")


def _ensure_unique_name(*, owner, name, exclude_id=None):
    queryset = Category.objects.filter(owner=owner, name=name)
    if exclude_id is not None:
        queryset = queryset.exclude(pk=exclude_id)
    if queryset.exists():
        raise ValidationError({"name": [DUPLICATE_CATEGORY_MESSAGE]})


def create_category(*, owner, name):
    name = _clean_category_name(name)
    _ensure_unique_name(owner=owner, name=name)

    try:
        with transaction.atomic():
            return Category.objects.create(owner=owner, name=name)
    except IntegrityError as exc:
        raise ValidationError({"name": [DUPLICATE_CATEGORY_MESSAGE]}) from exc


def rename_category(*, category, owner, name):
    _ensure_owner(category=category, owner=owner)
    name = _clean_category_name(name)
    _ensure_unique_name(owner=owner, name=name, exclude_id=category.pk)

    category.name = name
    try:
        with transaction.atomic():
            category.save(update_fields=["name", "updated_at"])
    except IntegrityError as exc:
        raise ValidationError({"name": [DUPLICATE_CATEGORY_MESSAGE]}) from exc

    return category


def delete_category(*, category, owner):
    _ensure_owner(category=category, owner=owner)
    category.delete()
