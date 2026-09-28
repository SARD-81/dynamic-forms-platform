from django.contrib.auth.hashers import make_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F, Max

from apps.core.selectors import get_category_for_owner

from .models import POSITIVE_INTEGER_MAX, Form, Question, QuestionOption
from .selectors import get_question_for_owner, get_questions_for_form_owner

FORM_NOT_DRAFT_MESSAGE = "Only draft forms can be edited or deleted."
FORM_PUBLISH_MESSAGE = "Only draft forms can be published."
FORM_CLOSE_MESSAGE = "Only published forms can be closed."
FORM_ACTIVE_RUN_MESSAGE = "This form cannot be closed while an active process run depends on it."
SCHEMA_NOT_DRAFT_MESSAGE = "Question schema can be changed only while the form is a draft."

_UNSET = object()


def _ensure_owner(*, form, owner):
    if form.owner_id != owner.pk:
        raise PermissionDenied("You do not own this form.")


def _lock_owned_draft_form(*, form_id, owner):
    form = Form.objects.select_for_update().get(pk=form_id)
    _ensure_owner(form=form, owner=owner)
    if form.status != Form.Status.DRAFT:
        raise ValidationError({"status": [SCHEMA_NOT_DRAFT_MESSAGE]})
    return form


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
    questions = list(form.questions.prefetch_related("options").order_by("order", "id"))
    if not questions:
        return ["Add at least one question before publishing."]

    errors = []
    expected_question_orders = list(range(1, len(questions) + 1))
    actual_question_orders = [question.order for question in questions]
    if actual_question_orders != expected_question_orders:
        errors.append("Question order must be contiguous and start at 1 before publishing.")

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
                errors.append(f"{label}: number questions cannot use text max length.")
            if (
                question.min_value is not None
                and question.max_value is not None
                and question.min_value > question.max_value
            ):
                errors.append(f"{label}: minimum value cannot be greater than maximum value.")
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
                errors.append(f"{label}: option order must be contiguous and start at 1.")

            normalized_labels = [option.label.strip() for option in options]
            if any(not option_label for option_label in normalized_labels):
                errors.append(f"{label}: option labels cannot be blank.")
            if len(set(normalized_labels)) != len(normalized_labels):
                errors.append(f"{label}: option labels must be unique.")

        else:
            errors.append(f"{label}: unsupported question type '{question.question_type}'.")

    return errors


def _validate_publication_readiness(*, form):
    errors = _publication_readiness_errors(form=form)
    if errors:
        raise ValidationError({"schema": errors})


def _validate_question_definition(
    *,
    text,
    question_type,
    max_length,
    min_value,
    max_value,
    has_options,
):
    text = text.strip()
    if not text:
        raise ValidationError({"text": ["Question text is required."]})

    if question_type not in Question.QuestionType.values:
        raise ValidationError({"question_type": ["Select a valid question type."]})

    if question_type == Question.QuestionType.TEXT:
        if max_length is not None and not 1 <= max_length <= POSITIVE_INTEGER_MAX:
            raise ValidationError(
                {"max_length": [f"Text max length must be between 1 and {POSITIVE_INTEGER_MAX}."]}
            )
        if min_value is not None or max_value is not None:
            raise ValidationError({"configuration": ["Text questions cannot use numeric bounds."]})
        if has_options:
            raise ValidationError({"options": ["Text questions cannot have options."]})

    elif question_type == Question.QuestionType.NUMBER:
        if max_length is not None:
            raise ValidationError(
                {"configuration": ["Number questions cannot use text max length."]}
            )
        if min_value is not None and max_value is not None and min_value > max_value:
            raise ValidationError(
                {"max_value": ["Maximum value must be greater than or equal to minimum value."]}
            )
        if has_options:
            raise ValidationError({"options": ["Number questions cannot have options."]})

    else:
        if max_length is not None or min_value is not None or max_value is not None:
            raise ValidationError(
                {
                    "configuration": [
                        "Select and checkbox questions cannot use text or numeric configuration."
                    ]
                }
            )

    return text


def _rewrite_question_orders(*, questions, ordered_ids):
    current_ids = [question.pk for question in questions]
    if len(ordered_ids) != len(set(ordered_ids)) or set(ordered_ids) != set(current_ids):
        raise ValidationError(
            {"question_ids": ["Provide every question exactly once when reordering."]}
        )
    if not questions:
        return

    offset = max(question.order for question in questions) + len(questions) + 1
    Question.objects.filter(pk__in=current_ids).update(order=F("order") + offset)

    by_id = {question.pk: question for question in questions}
    for order, question_id in enumerate(ordered_ids, start=1):
        question = by_id[question_id]
        question.order = order
        question.save(update_fields=["order"])


def _rewrite_option_orders(*, options, ordered_ids):
    current_ids = [option.pk for option in options]
    if len(ordered_ids) != len(set(ordered_ids)) or set(ordered_ids) != set(current_ids):
        raise ValidationError(
            {"option_ids": ["Provide every option exactly once when reordering."]}
        )
    if not options:
        return

    offset = max(option.order for option in options) + len(options) + 1
    QuestionOption.objects.filter(pk__in=current_ids).update(order=F("order") + offset)

    by_id = {option.pk: option for option in options}
    for order, option_id in enumerate(ordered_ids, start=1):
        option = by_id[option_id]
        option.order = order
        option.save(update_fields=["order"])


def _locked_question(*, form, question_id):
    question = Question.objects.select_for_update().filter(form=form, pk=question_id).first()
    if question is None:
        raise ValidationError({"question": ["Question does not belong to this form."]})
    return question


def _locked_option(*, question, option_id):
    option = (
        QuestionOption.objects.select_for_update().filter(question=question, pk=option_id).first()
    )
    if option is None:
        raise ValidationError({"option": ["Option does not belong to this question."]})
    return option


def _clean_option_label(label):
    label = label.strip()
    if not label:
        raise ValidationError({"label": ["Option label is required."]})

    max_length = QuestionOption._meta.get_field("label").max_length
    if len(label) > max_length:
        raise ValidationError(
            {"label": [f"Ensure this value has at most {max_length} characters."]}
        )
    return label


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


def create_question(
    *,
    form,
    owner,
    text,
    question_type,
    is_required=False,
    max_length=None,
    min_value=None,
    max_value=None,
):
    with transaction.atomic():
        locked_form = _lock_owned_draft_form(form_id=form.pk, owner=owner)
        text = _validate_question_definition(
            text=text,
            question_type=question_type,
            max_length=max_length,
            min_value=min_value,
            max_value=max_value,
            has_options=False,
        )
        next_order = (
            Question.objects.filter(form=locked_form).aggregate(max_order=Max("order"))["max_order"]
            or 0
        ) + 1
        return Question.objects.create(
            form=locked_form,
            text=text,
            question_type=question_type,
            is_required=is_required,
            order=next_order,
            max_length=max_length,
            min_value=min_value,
            max_value=max_value,
        )


def update_question(
    *,
    question,
    owner,
    text=_UNSET,
    question_type=_UNSET,
    is_required=_UNSET,
    max_length=_UNSET,
    min_value=_UNSET,
    max_value=_UNSET,
):
    with transaction.atomic():
        locked_form = _lock_owned_draft_form(form_id=question.form_id, owner=owner)
        locked_question = _locked_question(form=locked_form, question_id=question.pk)

        text = locked_question.text if text is _UNSET else text
        question_type = locked_question.question_type if question_type is _UNSET else question_type
        is_required = locked_question.is_required if is_required is _UNSET else is_required
        max_length = locked_question.max_length if max_length is _UNSET else max_length
        min_value = locked_question.min_value if min_value is _UNSET else min_value
        max_value = locked_question.max_value if max_value is _UNSET else max_value
        has_options = locked_question.options.exists()

        text = _validate_question_definition(
            text=text,
            question_type=question_type,
            max_length=max_length,
            min_value=min_value,
            max_value=max_value,
            has_options=has_options,
        )

        locked_question.text = text
        locked_question.question_type = question_type
        locked_question.is_required = is_required
        locked_question.max_length = max_length
        locked_question.min_value = min_value
        locked_question.max_value = max_value
        locked_question.save(
            update_fields=[
                "text",
                "question_type",
                "is_required",
                "max_length",
                "min_value",
                "max_value",
                "updated_at",
            ]
        )
        return get_question_for_owner(
            owner=owner,
            form_id=locked_form.pk,
            question_id=locked_question.pk,
        )


def delete_question(*, question, owner):
    with transaction.atomic():
        locked_form = _lock_owned_draft_form(form_id=question.form_id, owner=owner)
        locked_question = _locked_question(form=locked_form, question_id=question.pk)
        locked_question.delete()

        remaining = list(
            Question.objects.select_for_update().filter(form=locked_form).order_by("order", "id")
        )
        _rewrite_question_orders(
            questions=remaining,
            ordered_ids=[item.pk for item in remaining],
        )


def reorder_questions(*, form, owner, question_ids):
    with transaction.atomic():
        locked_form = _lock_owned_draft_form(form_id=form.pk, owner=owner)
        questions = list(
            Question.objects.select_for_update().filter(form=locked_form).order_by("order", "id")
        )
        _rewrite_question_orders(questions=questions, ordered_ids=question_ids)
        return list(
            get_questions_for_form_owner(
                owner=owner,
                form_id=locked_form.pk,
            )
        )


def move_question(*, question, owner, direction):
    if direction not in {"up", "down"}:
        raise ValidationError({"direction": ["Direction must be 'up' or 'down'."]})

    with transaction.atomic():
        locked_form = _lock_owned_draft_form(form_id=question.form_id, owner=owner)
        questions = list(
            Question.objects.select_for_update().filter(form=locked_form).order_by("order", "id")
        )
        ids = [item.pk for item in questions]
        if question.pk not in ids:
            raise ValidationError({"question": ["Question does not belong to this form."]})

        index = ids.index(question.pk)
        target = index - 1 if direction == "up" else index + 1
        if 0 <= target < len(ids):
            ids[index], ids[target] = ids[target], ids[index]
            _rewrite_question_orders(questions=questions, ordered_ids=ids)

        return _locked_question(form=locked_form, question_id=question.pk)


def create_question_option(*, question, owner, label):
    with transaction.atomic():
        locked_form = _lock_owned_draft_form(form_id=question.form_id, owner=owner)
        locked_question = _locked_question(form=locked_form, question_id=question.pk)
        if locked_question.question_type not in {
            Question.QuestionType.SELECT,
            Question.QuestionType.CHECKBOX,
        }:
            raise ValidationError(
                {"question_type": ["Options are allowed only for select and checkbox questions."]}
            )

        label = _clean_option_label(label)
        if locked_question.options.filter(label=label).exists():
            raise ValidationError({"label": ["Option labels must be unique per question."]})

        next_order = (
            locked_question.options.aggregate(max_order=Max("order"))["max_order"] or 0
        ) + 1
        return QuestionOption.objects.create(
            question=locked_question,
            label=label,
            order=next_order,
        )


def update_question_option(*, option, owner, label):
    with transaction.atomic():
        locked_form = _lock_owned_draft_form(
            form_id=option.question.form_id,
            owner=owner,
        )
        locked_question = _locked_question(
            form=locked_form,
            question_id=option.question_id,
        )
        locked_option = _locked_option(question=locked_question, option_id=option.pk)

        label = _clean_option_label(label)
        if locked_question.options.filter(label=label).exclude(pk=locked_option.pk).exists():
            raise ValidationError({"label": ["Option labels must be unique per question."]})

        locked_option.label = label
        locked_option.save(update_fields=["label"])
        return locked_option


def delete_question_option(*, option, owner):
    with transaction.atomic():
        locked_form = _lock_owned_draft_form(
            form_id=option.question.form_id,
            owner=owner,
        )
        locked_question = _locked_question(
            form=locked_form,
            question_id=option.question_id,
        )
        locked_option = _locked_option(question=locked_question, option_id=option.pk)
        locked_option.delete()

        remaining = list(
            QuestionOption.objects.select_for_update()
            .filter(question=locked_question)
            .order_by("order", "id")
        )
        _rewrite_option_orders(
            options=remaining,
            ordered_ids=[item.pk for item in remaining],
        )


def reorder_question_options(*, question, owner, option_ids):
    with transaction.atomic():
        locked_form = _lock_owned_draft_form(form_id=question.form_id, owner=owner)
        locked_question = _locked_question(form=locked_form, question_id=question.pk)
        if locked_question.question_type not in {
            Question.QuestionType.SELECT,
            Question.QuestionType.CHECKBOX,
        }:
            raise ValidationError(
                {"question_type": ["Only select and checkbox questions have options."]}
            )

        options = list(
            QuestionOption.objects.select_for_update()
            .filter(question=locked_question)
            .order_by("order", "id")
        )
        _rewrite_option_orders(options=options, ordered_ids=option_ids)
        return list(QuestionOption.objects.filter(question=locked_question).order_by("order", "id"))


def move_question_option(*, option, owner, direction):
    if direction not in {"up", "down"}:
        raise ValidationError({"direction": ["Direction must be 'up' or 'down'."]})

    with transaction.atomic():
        locked_form = _lock_owned_draft_form(
            form_id=option.question.form_id,
            owner=owner,
        )
        locked_question = _locked_question(
            form=locked_form,
            question_id=option.question_id,
        )
        options = list(
            QuestionOption.objects.select_for_update()
            .filter(question=locked_question)
            .order_by("order", "id")
        )
        ids = [item.pk for item in options]
        if option.pk not in ids:
            raise ValidationError({"option": ["Option does not belong to this question."]})

        index = ids.index(option.pk)
        target = index - 1 if direction == "up" else index + 1
        if 0 <= target < len(ids):
            ids[index], ids[target] = ids[target], ids[index]
            _rewrite_option_orders(options=options, ordered_ids=ids)

        return _locked_option(question=locked_question, option_id=option.pk)
