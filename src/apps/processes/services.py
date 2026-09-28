from django.contrib.auth.hashers import make_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F, Max

from apps.core.selectors import get_category_for_owner
from apps.forms.models import Form

from .models import Process, ProcessStep
from .selectors import get_process_steps_for_owner

PROCESS_NOT_DRAFT_MESSAGE = "Only draft processes can be edited or deleted."
PROCESS_PUBLISH_MESSAGE = "Only draft processes can be published."
PROCESS_CLOSE_MESSAGE = "Only published processes can be closed."
STEP_NOT_DRAFT_MESSAGE = "Process steps can be changed only while the process is a draft."

_UNSET = object()


def _ensure_owner(*, process, owner):
    if process.owner_id != owner.pk:
        raise PermissionDenied("You do not own this process.")


def _lock_owned_draft_process(*, process_id, owner):
    process = Process.objects.select_for_update().get(pk=process_id)
    _ensure_owner(process=process, owner=owner)
    if process.status != Process.Status.DRAFT:
        raise ValidationError({"status": [STEP_NOT_DRAFT_MESSAGE]})
    return process


def _clean_title(title):
    title = title.strip()
    if not title:
        raise ValidationError({"title": ["This field is required."]})
    if len(title) > 200:
        raise ValidationError({"title": ["Ensure this value has at most 200 characters."]})
    return title


def _validate_process_type(process_type):
    if process_type not in Process.ProcessType.values:
        raise ValidationError({"process_type": ["Select a valid process type."]})


def _validate_visibility(visibility):
    if visibility not in Process.Visibility.values:
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
    existing_process=None,
):
    if visibility == Process.Visibility.PUBLIC:
        return None

    if access_password:
        return make_password(access_password)

    if (
        existing_process is not None
        and existing_process.visibility == Process.Visibility.PRIVATE
        and existing_process.access_password_hash
    ):
        return existing_process.access_password_hash

    raise ValidationError({"access_password": ["A password is required for private processes."]})


def _validate_publication_readiness(*, process):
    steps = list(process.steps.select_related("form").order_by("order", "id"))
    if not steps:
        raise ValidationError({"steps": ["Add at least one step before publishing."]})

    errors = {}
    expected_orders = list(range(1, len(steps) + 1))
    actual_orders = [s.order for s in steps]
    if actual_orders != expected_orders:
        errors["order"] = ["Step order must be contiguous and start at 1 before publishing."]

    form_ids = [s.form_id for s in steps]
    if len(form_ids) != len(set(form_ids)):
        errors["steps"] = ["Each form can only be attached once in a process."]

    for step in steps:
        if step.form.status != Form.Status.PUBLISHED:
            errors.setdefault("forms", []).append(
                f"Form '{step.form.title}' must be published before the process can be published."
            )

    if process.visibility == Process.Visibility.PRIVATE and not process.access_password_hash:
        errors["access_password"] = ["A private process must have a valid password set."]

    if errors:
        raise ValidationError(errors)


def _rewrite_step_orders(*, steps, ordered_ids):
    current_ids = [step.pk for step in steps]
    if len(ordered_ids) != len(set(ordered_ids)) or set(ordered_ids) != set(current_ids):
        raise ValidationError({"step_ids": ["Provide every step exactly once when reordering."]})
    if not steps:
        return

    offset = max(step.order for step in steps) + len(steps) + 1
    ProcessStep.objects.filter(pk__in=current_ids).update(order=F("order") + offset)

    by_id = {step.pk: step for step in steps}
    for order, step_id in enumerate(ordered_ids, start=1):
        step = by_id[step_id]
        step.order = order
        step.save(update_fields=["order"])


def create_process(
    *,
    owner,
    title,
    process_type,
    description="",
    category_id=None,
    visibility=Process.Visibility.PUBLIC,
    access_password=None,
):
    title = _clean_title(title)
    _validate_process_type(process_type)
    _validate_visibility(visibility)
    category = _category_for_owner(owner=owner, category_id=category_id)
    password_hash = _password_hash_for_visibility(
        visibility=visibility,
        access_password=access_password,
    )

    with transaction.atomic():
        return Process.objects.create(
            owner=owner,
            title=title,
            description=description.strip(),
            category=category,
            process_type=process_type,
            visibility=visibility,
            access_password_hash=password_hash,
            status=Process.Status.DRAFT,
        )


def update_draft_process(
    *,
    process,
    owner,
    title=_UNSET,
    description=_UNSET,
    process_type=_UNSET,
    category_id=_UNSET,
    visibility=_UNSET,
    access_password=_UNSET,
):
    with transaction.atomic():
        locked_process = Process.objects.select_for_update().get(pk=process.pk)
        _ensure_owner(process=locked_process, owner=owner)

        if locked_process.status != Process.Status.DRAFT:
            raise ValidationError({"status": [PROCESS_NOT_DRAFT_MESSAGE]})

        update_fields = ["updated_at"]

        if title is not _UNSET:
            locked_process.title = _clean_title(title)
            update_fields.append("title")

        if description is not _UNSET:
            locked_process.description = (description or "").strip()
            update_fields.append("description")

        if process_type is not _UNSET:
            _validate_process_type(process_type)
            locked_process.process_type = process_type
            update_fields.append("process_type")

        if category_id is not _UNSET:
            locked_process.category = _category_for_owner(owner=owner, category_id=category_id)
            update_fields.append("category")

        next_visibility = locked_process.visibility if visibility is _UNSET else visibility
        if visibility is not _UNSET:
            _validate_visibility(next_visibility)
            locked_process.visibility = next_visibility
            update_fields.append("visibility")

        if visibility is not _UNSET or access_password is not _UNSET:
            locked_process.access_password_hash = _password_hash_for_visibility(
                visibility=next_visibility,
                access_password=None if access_password is _UNSET else access_password,
                existing_process=locked_process,
            )
            update_fields.append("access_password_hash")

        locked_process.save(update_fields=list(dict.fromkeys(update_fields)))
        return locked_process


def delete_draft_process(*, process, owner):
    with transaction.atomic():
        locked_process = Process.objects.select_for_update().get(pk=process.pk)
        _ensure_owner(process=locked_process, owner=owner)

        if locked_process.status != Process.Status.DRAFT:
            raise ValidationError({"status": [PROCESS_NOT_DRAFT_MESSAGE]})

        locked_process.delete()


def publish_process(*, process, owner):
    with transaction.atomic():
        locked_process = Process.objects.select_for_update().get(pk=process.pk)
        _ensure_owner(process=locked_process, owner=owner)

        if locked_process.status != Process.Status.DRAFT:
            raise ValidationError({"status": [PROCESS_PUBLISH_MESSAGE]})

        _validate_publication_readiness(process=locked_process)

        locked_process.status = Process.Status.PUBLISHED
        locked_process.save(update_fields=["status", "updated_at"])
        return locked_process


def close_process(*, process, owner):
    with transaction.atomic():
        locked_process = Process.objects.select_for_update().get(pk=process.pk)
        _ensure_owner(process=locked_process, owner=owner)

        if locked_process.status != Process.Status.PUBLISHED:
            raise ValidationError({"status": [PROCESS_CLOSE_MESSAGE]})

        locked_process.status = Process.Status.CLOSED
        locked_process.save(update_fields=["status", "updated_at"])
        return locked_process


def create_process_step(*, process, owner, form_id):
    with transaction.atomic():
        locked_process = _lock_owned_draft_process(process_id=process.pk, owner=owner)

        form = Form.objects.filter(pk=form_id, owner=owner).first()
        if form is None:
            raise ValidationError(
                {"form_id": ["Selected form is invalid or does not belong to you."]}
            )

        if ProcessStep.objects.filter(process=locked_process, form=form).exists():
            raise ValidationError({"form_id": ["This form is already attached to this process."]})

        next_order = (
            ProcessStep.objects.filter(process=locked_process).aggregate(max_order=Max("order"))[
                "max_order"
            ]
            or 0
        ) + 1

        return ProcessStep.objects.create(
            process=locked_process,
            form=form,
            order=next_order,
        )


def delete_process_step(*, process, owner, step_id):
    with transaction.atomic():
        locked_process = _lock_owned_draft_process(process_id=process.pk, owner=owner)
        step = (
            ProcessStep.objects.select_for_update()
            .filter(process=locked_process, pk=step_id)
            .first()
        )
        if step is None:
            raise ValidationError({"step": ["Step does not belong to this process."]})

        step.delete()

        remaining_steps = list(
            ProcessStep.objects.select_for_update()
            .filter(process=locked_process)
            .order_by("order", "id")
        )
        _rewrite_step_orders(
            steps=remaining_steps,
            ordered_ids=[s.pk for s in remaining_steps],
        )


def reorder_process_steps(*, process, owner, step_ids):
    with transaction.atomic():
        locked_process = _lock_owned_draft_process(process_id=process.pk, owner=owner)
        steps = list(
            ProcessStep.objects.select_for_update()
            .filter(process=locked_process)
            .order_by("order", "id")
        )
        _rewrite_step_orders(steps=steps, ordered_ids=step_ids)
        return list(
            get_process_steps_for_owner(
                owner=owner,
                process_id=locked_process.pk,
            )
        )
