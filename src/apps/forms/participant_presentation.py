from copy import deepcopy

from django.core.exceptions import ValidationError

from .models import Question


def participant_form_context(*, read_model, post_data=None, validation_errors=None):
    model = deepcopy(read_model)
    validation_errors = validation_errors or {}
    known_question_error_keys = set()

    for question in model["questions"]:
        field_name = f"q_{question['id']}"
        error_key = f"question_{question['id']}"
        known_question_error_keys.add(error_key)
        question["field_name"] = field_name
        question["errors"] = validation_errors.get(error_key, [])
        question["value"] = ""

        if post_data is None:
            for option in question["options"]:
                option["selected"] = False
            continue

        if question["question_type"] == Question.QuestionType.CHECKBOX:
            selected = set(post_data.getlist(field_name))
            for option in question["options"]:
                option["selected"] = str(option["id"]) in selected
        elif question["question_type"] == Question.QuestionType.SELECT:
            selected = post_data.get(field_name, "")
            question["value"] = selected
            for option in question["options"]:
                option["selected"] = str(option["id"]) == selected
        else:
            question["value"] = post_data.get(field_name, "")
            for option in question["options"]:
                option["selected"] = False

    general_errors = []
    for key, messages in validation_errors.items():
        if key not in known_question_error_keys:
            general_errors.extend(messages)

    return {
        "participant_form": model,
        "submission_errors": general_errors,
        "has_submission_errors": bool(validation_errors),
    }


def html_submission_answers(*, read_model, post_data):
    answers = []
    errors = {}
    known_names = set()

    for question in read_model["questions"]:
        field_name = f"q_{question['id']}"
        known_names.add(field_name)
        values = post_data.getlist(field_name)
        if not values:
            continue

        error_key = f"question_{question['id']}"
        if question["question_type"] == Question.QuestionType.CHECKBOX:
            answers.append(
                {
                    "question_id": question["id"],
                    "option_ids": values,
                }
            )
            continue

        if len(values) > 1:
            errors.setdefault(error_key, []).append(
                "Multiple values for a single-value question are not allowed."
            )
            continue

        value = values[0]
        if question["question_type"] == Question.QuestionType.SELECT:
            if value == "":
                continue
            answers.append(
                {
                    "question_id": question["id"],
                    "option_ids": [value],
                }
            )
        elif question["question_type"] == Question.QuestionType.TEXT:
            answers.append(
                {
                    "question_id": question["id"],
                    "text_value": value,
                }
            )
        else:
            answers.append(
                {
                    "question_id": question["id"],
                    "number_value": value,
                }
            )

    # Do not silently ignore forged question fields from another Form.
    for field_name in post_data:
        if not field_name.startswith("q_") or field_name in known_names:
            continue
        values = post_data.getlist(field_name)
        if len(values) > 1:
            errors.setdefault("answers", []).append(
                "Multiple values for a single-value question are not allowed."
            )
            continue
        if values:
            answers.append(
                {
                    "question_id": field_name.removeprefix("q_"),
                    "text_value": values[0],
                }
            )

    if errors:
        raise ValidationError(errors)
    return answers
