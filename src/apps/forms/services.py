from django.contrib.auth.hashers import make_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.core.selectors import get_category_for_owner

from .models import Form, Question

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


def _publication_readiness_errors(*, form):
    questions = list(
        form.questions.prefetch_related("options").order_by("order", "id")
    )
    if not questions:
        return ["Add at least one question before publishing."]

    errors = []
    expected_question_orders = list(range(1, len(questions) + 1))
    actual_question_orders = [question.order for question in questions]
    if actual_question_orders != expected_question_orders:
        errors.append(
            "Question order must be contiguous and start at 1 before publishing."
        )

    for question in questions:
        label = f"Question {question.order}"
        options = sorted(
            question.options.all(),
            key=lambda option: (option.order, option.pk),
        )

        if not question.text.strip():
            errors.append(f"{label}: question text is required.")

        if question.question_type == Question.QuestionType.TEXT:
            if question.max_length is not None and question.max_length < 1:
                errors.append(f"{label}: text max length must be at least 1.")
            if question.min_value is not None or question.max_value is not None:
                errors.append(f"{label}: text questions cannot use numeric bounds.")
            if options:
                errors.append(f"{label}: text questions cannot have options.")

        elif question.question_type == Question.QuestionType.NUMBER:
            if question.max_length is not None:
                errors.append(
                    f"{label}: number questions cannot use text max length."
                )
            if (
                question.min_value is not None
                and question.max_value is not None
                and question.min_value > question.max_value
            ):
                errors.append(
                    f"{label}: minimum value cannot be greater than maximum value."
                )
            if options:
                errors.append(f"{label}: number questions cannot have options.")

        elif question.question_type in {
            Question.QuestionType.SELECT,
            Question.QuestionType.CHECKBOX,
        }:
            if (
                question.max_length is not None
                or question.min_value is not None
                or question.max_value is not None
            ):
                errors.append(
                    f"{label}: option questions cannot use text or numeric configuration."
                )

            if not options:
                errors.append(
                    f"{label}: {question.get_question_type_display()} questions "
                    "need at least one option before publishing."
                )
                continue

            expected_option_orders = list(range(1, len(options) + 1))
            actual_option_orders = [option.order for option in options]
            if actual_option_orders != expected_option_orders:
                errors.append(
                    f"{label}: option order must be contiguous and start at 1."
                )

            normalized_labels = [option.label.strip() for option in options]
            if any(not option_label for option_label in normalized_labels):
                errors.append(f"{label}: option labels cannot be blank.")
            if len(set(normalized_labels)) != len(normalized_labels):
                errors.append(f"{label}: option labels must be unique.")

        else:
            errors.append(
                f"{label}: unsupported question type '{question.question_type}'."
            )

    return errors


def _validate_publication_readiness(*, form):
    errors = _publication_readiness_errors(form=form)
    if errors:
        raise ValidationError({"schema": errors})


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

        _validate_publication_readiness(form=locked_form)

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
