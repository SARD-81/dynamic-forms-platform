from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.validators import DecimalValidator
from django.db import transaction
from django.db.models import Prefetch

from .models import Answer, AnswerOption, Form, FormSubmission, Question, QuestionOption
from .report_cache import invalidate_form_report_cache

FORM_SUBMISSION_STATUS_MESSAGE = "Only published forms accept submissions."


def _add_error(errors, key, message):
    errors.setdefault(key, []).append(message)


def _question_error_key(question_id):
    return f"question_{question_id}"


def _parse_positive_id(value, *, field_name):
    if isinstance(value, bool):
        raise ValidationError({field_name: ["A positive integer ID is required."]})
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({field_name: ["A positive integer ID is required."]}) from exc

    if isinstance(value, (float, Decimal)) and value != parsed:
        raise ValidationError({field_name: ["A positive integer ID is required."]})
    if parsed < 1:
        raise ValidationError({field_name: ["A positive integer ID is required."]})
    return parsed


def _parse_number(value, *, question, errors):
    key = _question_error_key(question.pk)
    if value in (None, ""):
        if question.is_required:
            _add_error(errors, key, "This question is required.")
        return None

    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        _add_error(errors, key, "Enter a valid number.")
        return None

    if not number.is_finite():
        _add_error(errors, key, "Enter a finite number.")
        return None

    number_field = Answer._meta.get_field("number_value")
    validator = DecimalValidator(
        max_digits=number_field.max_digits,
        decimal_places=number_field.decimal_places,
    )
    try:
        validator(number)
    except ValidationError:
        _add_error(
            errors,
            key,
            (
                "Enter a number with at most "
                f"{number_field.max_digits} digits and "
                f"{number_field.decimal_places} decimal places."
            ),
        )
        return None

    if question.min_value is not None and number < question.min_value:
        _add_error(errors, key, f"Value must be at least {question.min_value}.")
    if question.max_value is not None and number > question.max_value:
        _add_error(errors, key, f"Value must be at most {question.max_value}.")
    return number


def _validate_text_answer(*, question, payload, errors):
    key = _question_error_key(question.pk)
    if "number_value" in payload or "option_ids" in payload:
        _add_error(errors, key, "Text questions accept only text_value.")
        return None

    value = payload.get("text_value")
    if value is None:
        value = ""
    if not isinstance(value, str):
        value = str(value)

    if not value.strip():
        if question.is_required:
            _add_error(errors, key, "This question is required.")
        return None

    if question.max_length is not None and len(value) > question.max_length:
        _add_error(
            errors,
            key,
            f"Response must be at most {question.max_length} characters.",
        )
        return None

    return {"question": question, "text_value": value}


def _validate_number_answer(*, question, payload, errors):
    key = _question_error_key(question.pk)
    if "text_value" in payload or "option_ids" in payload:
        _add_error(errors, key, "Number questions accept only number_value.")
        return None

    number = _parse_number(
        payload.get("number_value"),
        question=question,
        errors=errors,
    )
    if number is None:
        return None
    return {"question": question, "number_value": number}


def _coerce_option_ids(*, question, payload, errors):
    key = _question_error_key(question.pk)
    raw_ids = payload.get("option_ids")
    if raw_ids is None:
        raw_ids = []
    if not isinstance(raw_ids, (list, tuple)):
        _add_error(errors, key, "option_ids must be a list.")
        return []

    option_ids = []
    for raw_id in raw_ids:
        try:
            option_ids.append(_parse_positive_id(raw_id, field_name=key))
        except ValidationError as exc:
            for message in exc.message_dict[key]:
                _add_error(errors, key, message)

    if len(option_ids) != len(set(option_ids)):
        _add_error(errors, key, "Duplicate option IDs are not allowed.")
    return option_ids


def _validate_option_answer(
    *,
    question,
    payload,
    errors,
):
    key = _question_error_key(question.pk)
    if "text_value" in payload or "number_value" in payload:
        _add_error(errors, key, "Choice questions accept only option_ids.")
        return None

    option_ids = _coerce_option_ids(question=question, payload=payload, errors=errors)
    if len(option_ids) != len(set(option_ids)):
        return None

    if question.question_type == Question.QuestionType.SELECT:
        if not option_ids:
            if question.is_required:
                _add_error(errors, key, "This question is required.")
            return None
        if len(option_ids) != 1:
            _add_error(errors, key, "Select questions require exactly one option.")
            return None
    elif not option_ids:
        if question.is_required:
            _add_error(errors, key, "Select at least one option.")
        return None

    options_by_id = {option.pk: option for option in question.options.all()}
    selected_options = []
    for option_id in option_ids:
        option = options_by_id.get(option_id)
        if option is None:
            _add_error(errors, key, "Invalid option ID for this question.")
            continue
        selected_options.append(option)

    if len(selected_options) != len(option_ids):
        return None
    return {"question": question, "options": selected_options}


def _validate_submission_payload(*, form, answers):
    if not isinstance(answers, (list, tuple)):
        raise ValidationError({"answers": ["Answers must be provided as a list."]})

    questions = list(
        Question.objects.filter(form=form)
        .prefetch_related(
            Prefetch(
                "options",
                queryset=QuestionOption.objects.order_by("order", "id"),
            )
        )
        .order_by("order", "id")
    )
    questions_by_id = {question.pk: question for question in questions}

    errors = {}
    payload_by_question_id = {}
    supplied_question_ids = []

    for index, payload in enumerate(answers):
        if not isinstance(payload, dict):
            _add_error(errors, "answers", f"Answer {index + 1} must be an object.")
            continue
        if "question_id" not in payload:
            _add_error(errors, "answers", f"Answer {index + 1} is missing question_id.")
            continue

        try:
            question_id = _parse_positive_id(
                payload["question_id"],
                field_name="answers",
            )
        except ValidationError as exc:
            for message in exc.message_dict["answers"]:
                _add_error(errors, "answers", message)
            continue

        supplied_question_ids.append(question_id)
        if question_id in payload_by_question_id:
            _add_error(
                errors,
                _question_error_key(question_id),
                "Duplicate answers for one question are not allowed.",
            )
            continue
        payload_by_question_id[question_id] = payload

    supplied_set = set(supplied_question_ids)
    invalid_question_ids = supplied_set - set(questions_by_id)
    for question_id in sorted(invalid_question_ids):
        _add_error(
            errors,
            _question_error_key(question_id),
            "Invalid question ID for this form.",
        )

    for question in questions:
        if question.is_required and question.pk not in payload_by_question_id:
            _add_error(
                errors,
                _question_error_key(question.pk),
                "This question is required.",
            )

    validated = []
    for question_id, payload in payload_by_question_id.items():
        question = questions_by_id.get(question_id)
        if question is None:
            continue

        if question.question_type == Question.QuestionType.TEXT:
            answer = _validate_text_answer(
                question=question,
                payload=payload,
                errors=errors,
            )
        elif question.question_type == Question.QuestionType.NUMBER:
            if "text_value" in payload or "option_ids" in payload:
                _add_error(
                    errors,
                    _question_error_key(question.pk),
                    "Number questions accept only number_value.",
                )
                answer = None
            else:
                answer = _validate_number_answer(
                    question=question,
                    payload=payload,
                    errors=errors,
                )
        else:
            answer = _validate_option_answer(
                question=question,
                payload=payload,
                errors=errors,
            )

        if answer is not None:
            validated.append(answer)

    if errors:
        raise ValidationError(errors)
    return validated


def submit_form(*, form, answers, respondent=None):
    """Validate and atomically persist one Form submission.

    Forms remains independent from Processes. Future Process execution may call
    this Service and attach the returned FormSubmission from the Processes side.
    """

    with transaction.atomic():
        locked_form = Form.objects.select_for_update().get(pk=form.pk)
        if locked_form.status != Form.Status.PUBLISHED:
            raise ValidationError({"form": [FORM_SUBMISSION_STATUS_MESSAGE]})

        validated_answers = _validate_submission_payload(
            form=locked_form,
            answers=answers,
        )

        submission = FormSubmission.objects.create(
            form=locked_form,
            respondent=respondent,
        )
        for item in validated_answers:
            question = item["question"]
            answer = Answer.objects.create(
                submission=submission,
                question=question,
                text_value=item.get("text_value"),
                number_value=item.get("number_value"),
            )
            options = item.get("options", [])
            if options:
                AnswerOption.objects.bulk_create(
                    [AnswerOption(answer=answer, option=option) for option in options]
                )

        report_form_id = locked_form.pk
        transaction.on_commit(
            lambda: invalidate_form_report_cache(form_id=report_form_id)
        )
        return submission
