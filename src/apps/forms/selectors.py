from .models import Form


def get_forms_for_owner(*, owner):
    return (
        Form.objects.filter(owner=owner).select_related("category").order_by("-created_at", "-id")
    )


def get_form_for_owner(*, owner, form_id):
    return get_forms_for_owner(owner=owner).filter(pk=form_id).first()
