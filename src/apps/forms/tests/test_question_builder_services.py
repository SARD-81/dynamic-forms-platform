from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.forms.models import Form, Question, QuestionOption
from apps.forms.services import (
    create_question,
    create_question_option,
    delete_question,
    delete_question_option,
    publish_form,
    reorder_question_options,
    reorder_questions,
    update_question,
    update_question_option,
)


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="builder-service-other",
        email="builder-service-other@example.com",
        password="test-password",
    )


@pytest.fixture
def draft_form(user):
    return Form.objects.create(owner=user, title="Builder form")


@pytest.mark.django_db
def test_create_question_supports_all_frozen_types(user, draft_form):
    text = create_question(
        form=draft_form,
        owner=user,
        text="Your name",
        question_type=Question.QuestionType.TEXT,
        is_required=True,
        max_length=120,
    )
    number = create_question(
        form=draft_form,
        owner=user,
        text="Years of experience",
        question_type=Question.QuestionType.NUMBER,
        min_value=Decimal("0"),
        max_value=Decimal("50"),
    )
    select = create_question(
        form=draft_form,
        owner=user,
        text="Department",
        question_type=Question.QuestionType.SELECT,
    )
    checkbox = create_question(
        form=draft_form,
        owner=user,
        text="Skills",
        question_type=Question.QuestionType.CHECKBOX,
    )

    assert [text.order, number.order, select.order, checkbox.order] == [1, 2, 3, 4]
    assert text.max_length == 120
    assert number.min_value == Decimal("0")
    assert number.max_value == Decimal("50")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("question_type", "kwargs", "field"),
    [
        (
            Question.QuestionType.TEXT,
            {"min_value": Decimal("1")},
            "configuration",
        ),
        (
            Question.QuestionType.NUMBER,
            {"max_length": 20},
            "configuration",
        ),
        (
            Question.QuestionType.SELECT,
            {"max_length": 20},
            "configuration",
        ),
    ],
)
def test_create_question_rejects_incompatible_configuration(
    user,
    draft_form,
    question_type,
    kwargs,
    field,
):
    with pytest.raises(ValidationError) as exc_info:
        create_question(
            form=draft_form,
            owner=user,
            text="Invalid",
            question_type=question_type,
            **kwargs,
        )

    assert field in exc_info.value.message_dict


@pytest.mark.django_db
def test_text_question_rejects_max_length_outside_database_range(user, draft_form):
    with pytest.raises(ValidationError) as exc_info:
        create_question(
            form=draft_form,
            owner=user,
            text="Too large",
            question_type=Question.QuestionType.TEXT,
            max_length=2_147_483_648,
        )

    assert "max_length" in exc_info.value.message_dict


@pytest.mark.django_db
def test_number_question_rejects_inverted_bounds(user, draft_form):
    with pytest.raises(ValidationError) as exc_info:
        create_question(
            form=draft_form,
            owner=user,
            text="Range",
            question_type=Question.QuestionType.NUMBER,
            min_value=Decimal("10"),
            max_value=Decimal("1"),
        )

    assert "max_value" in exc_info.value.message_dict


@pytest.mark.django_db
def test_option_management_requires_option_question_and_unique_label(user, draft_form):
    text = create_question(
        form=draft_form,
        owner=user,
        text="Text",
        question_type=Question.QuestionType.TEXT,
    )
    select = create_question(
        form=draft_form,
        owner=user,
        text="Select",
        question_type=Question.QuestionType.SELECT,
    )

    with pytest.raises(ValidationError):
        create_question_option(question=text, owner=user, label="Not allowed")

    first = create_question_option(question=select, owner=user, label="  Alpha  ")
    assert first.label == "Alpha"

    with pytest.raises(ValidationError) as exc_info:
        create_question_option(question=select, owner=user, label="Alpha")

    assert "label" in exc_info.value.message_dict


@pytest.mark.django_db
def test_option_service_rejects_label_longer_than_model_limit_on_create_and_update(
    user,
    draft_form,
):
    question = create_question(
        form=draft_form,
        owner=user,
        text="Choice",
        question_type=Question.QuestionType.SELECT,
    )
    existing = create_question_option(question=question, owner=user, label="Existing")
    max_length = QuestionOption._meta.get_field("label").max_length
    too_long_label = "x" * (max_length + 1)

    with pytest.raises(ValidationError) as create_error:
        create_question_option(
            question=question,
            owner=user,
            label=too_long_label,
        )
    assert "label" in create_error.value.message_dict

    with pytest.raises(ValidationError) as update_error:
        update_question_option(
            option=existing,
            owner=user,
            label=too_long_label,
        )
    assert "label" in update_error.value.message_dict

    existing.refresh_from_db()
    assert existing.label == "Existing"


@pytest.mark.django_db
def test_question_type_change_rejects_existing_options(user, draft_form):
    question = create_question(
        form=draft_form,
        owner=user,
        text="Choice",
        question_type=Question.QuestionType.SELECT,
    )
    create_question_option(question=question, owner=user, label="One")

    with pytest.raises(ValidationError) as exc_info:
        update_question(
            question=question,
            owner=user,
            question_type=Question.QuestionType.TEXT,
            max_length=100,
        )

    assert "options" in exc_info.value.message_dict


@pytest.mark.django_db
def test_question_reorder_and_delete_keep_contiguous_order(user, draft_form):
    first = create_question(
        form=draft_form,
        owner=user,
        text="First",
        question_type=Question.QuestionType.TEXT,
    )
    second = create_question(
        form=draft_form,
        owner=user,
        text="Second",
        question_type=Question.QuestionType.TEXT,
    )
    third = create_question(
        form=draft_form,
        owner=user,
        text="Third",
        question_type=Question.QuestionType.TEXT,
    )

    reordered = reorder_questions(
        form=draft_form,
        owner=user,
        question_ids=[third.id, first.id, second.id],
    )

    assert [(item.id, item.order) for item in reordered] == [
        (third.id, 1),
        (first.id, 2),
        (second.id, 3),
    ]

    delete_question(question=first, owner=user)
    remaining = list(Question.objects.filter(form=draft_form).order_by("order"))

    assert [(item.id, item.order) for item in remaining] == [
        (third.id, 1),
        (second.id, 2),
    ]


@pytest.mark.django_db
def test_option_reorder_and_delete_keep_contiguous_order(user, draft_form):
    question = create_question(
        form=draft_form,
        owner=user,
        text="Choice",
        question_type=Question.QuestionType.CHECKBOX,
    )
    first = create_question_option(question=question, owner=user, label="First")
    second = create_question_option(question=question, owner=user, label="Second")
    third = create_question_option(question=question, owner=user, label="Third")

    reordered = reorder_question_options(
        question=question,
        owner=user,
        option_ids=[third.id, first.id, second.id],
    )

    assert [(item.id, item.order) for item in reordered] == [
        (third.id, 1),
        (first.id, 2),
        (second.id, 3),
    ]

    delete_question_option(option=first, owner=user)
    remaining = list(QuestionOption.objects.filter(question=question).order_by("order"))

    assert [(item.id, item.order) for item in remaining] == [
        (third.id, 1),
        (second.id, 2),
    ]


@pytest.mark.django_db
def test_reorder_requires_complete_unique_id_set(user, draft_form):
    first = create_question(
        form=draft_form,
        owner=user,
        text="First",
        question_type=Question.QuestionType.TEXT,
    )
    second = create_question(
        form=draft_form,
        owner=user,
        text="Second",
        question_type=Question.QuestionType.TEXT,
    )

    with pytest.raises(ValidationError):
        reorder_questions(
            form=draft_form,
            owner=user,
            question_ids=[first.id, first.id],
        )

    with pytest.raises(ValidationError):
        reorder_questions(
            form=draft_form,
            owner=user,
            question_ids=[first.id],
        )

    assert list(Question.objects.filter(form=draft_form).values_list("id", "order")) == [
        (first.id, 1),
        (second.id, 2),
    ]


@pytest.mark.django_db
def test_reorder_rejects_foreign_ids_when_collection_is_empty(user, draft_form):
    with pytest.raises(ValidationError) as question_error:
        reorder_questions(
            form=draft_form,
            owner=user,
            question_ids=[999999],
        )
    assert "question_ids" in question_error.value.message_dict

    question = create_question(
        form=draft_form,
        owner=user,
        text="Empty options",
        question_type=Question.QuestionType.SELECT,
    )
    with pytest.raises(ValidationError) as option_error:
        reorder_question_options(
            question=question,
            owner=user,
            option_ids=[999999],
        )
    assert "option_ids" in option_error.value.message_dict


@pytest.mark.django_db
def test_schema_services_reject_all_mutation_after_publish(user, draft_form):
    question = create_question(
        form=draft_form,
        owner=user,
        text="Choice",
        question_type=Question.QuestionType.SELECT,
    )
    option = create_question_option(question=question, owner=user, label="One")
    published = publish_form(form=draft_form, owner=user)

    operations = [
        lambda: create_question(
            form=published,
            owner=user,
            text="Late",
            question_type=Question.QuestionType.TEXT,
        ),
        lambda: update_question(question=question, owner=user, text="Changed"),
        lambda: delete_question(question=question, owner=user),
        lambda: reorder_questions(
            form=published,
            owner=user,
            question_ids=[question.id],
        ),
        lambda: create_question_option(question=question, owner=user, label="Two"),
        lambda: update_question_option(option=option, owner=user, label="Changed"),
        lambda: delete_question_option(option=option, owner=user),
        lambda: reorder_question_options(
            question=question,
            owner=user,
            option_ids=[option.id],
        ),
    ]

    for operation in operations:
        with pytest.raises(ValidationError) as exc_info:
            operation()
        assert "status" in exc_info.value.message_dict


@pytest.mark.django_db
def test_schema_service_rejects_cross_owner_management(user, other_user):
    foreign_form = Form.objects.create(owner=other_user, title="Foreign")

    with pytest.raises(PermissionDenied):
        create_question(
            form=foreign_form,
            owner=user,
            text="Forbidden",
            question_type=Question.QuestionType.TEXT,
        )
