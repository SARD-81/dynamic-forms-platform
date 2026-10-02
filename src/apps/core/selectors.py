from .models import Category


def get_category_choices_for_owner(*, owner):
    """Return categories that can be selected by the given owner."""
    return Category.objects.filter(owner=owner).order_by("name", "id")


def get_category_for_owner(*, owner, category_id):
    return get_category_choices_for_owner(owner=owner).filter(pk=category_id).first()
