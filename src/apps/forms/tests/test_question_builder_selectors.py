import pytest

from apps.accounts.models import User
from apps.forms.models import Form, Question, QuestionOption
from apps.forms.selectors import (
    get_option_for_owner,
    get_question_for_owner,
    get_questions_for_form_owner,
)


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="builder-selector-other",
        email="builder-selector-other@example.com",
        password="test-password",
    )


@pytest.mark.django_db
def test_question_and_option_selectors_are_owner_scoped(user, other_user):
    form = Form.objects.create(owner=user, title="Owned")
    question = Question.objects.create(
        form=form,
        text="Visible",
        question_type=Question.QuestionType.SELECT,
        order=1,
    )
    second_option = QuestionOption.objects.create(
        question=question,
        label="Second option",
        order=2,
    )
    option = QuestionOption.objects.create(
        question=question,
        label="Visible option",
        order=1,
    )

    foreign_form = Form.objects.create(owner=other_user, title="Foreign")
    foreign_question = Question.objects.create(
        form=foreign_form,
        text="Hidden",
        question_type=Question.QuestionType.TEXT,
        order=1,
    )

    selected_questions = list(get_questions_for_form_owner(owner=user, form_id=form.id))
    assert selected_questions == [question]
    assert list(selected_questions[0].options.all()) == [option, second_option]
    assert (
        get_question_for_owner(
            owner=user,
            form_id=foreign_form.id,
            question_id=foreign_question.id,
        )
        is None
    )
    assert (
        get_option_for_owner(
            owner=user,
            form_id=form.id,
            question_id=question.id,
            option_id=option.id,
        )
        == option
    )
