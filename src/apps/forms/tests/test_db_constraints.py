from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import User
from apps.forms.models import (
    Answer,
    AnswerOption,
    Form,
    FormSubmission,
    Question,
    QuestionOption,
)


class FormDatabaseConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="form-owner",
            email="form-owner@example.com",
            password="test-password",
        )
        self.form = Form.objects.create(
            owner=self.user,
            title="Constraint Form",
            visibility=Form.Visibility.PUBLIC,
            status=Form.Status.DRAFT,
        )

    def test_private_form_requires_password_hash(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Form.objects.create(
                    owner=self.user,
                    title="Private without password",
                    visibility=Form.Visibility.PRIVATE,
                    access_password_hash=None,
                )

    def test_question_order_must_start_at_one(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Question.objects.create(
                    form=self.form,
                    text="Invalid order",
                    question_type=Question.QuestionType.TEXT,
                    order=0,
                )

    def test_question_order_is_unique_per_form(self):
        Question.objects.create(
            form=self.form,
            text="First",
            question_type=Question.QuestionType.TEXT,
            order=1,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Question.objects.create(
                    form=self.form,
                    text="Duplicate order",
                    question_type=Question.QuestionType.TEXT,
                    order=1,
                )

    def test_numeric_question_min_cannot_exceed_max(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Question.objects.create(
                    form=self.form,
                    text="Invalid bounds",
                    question_type=Question.QuestionType.NUMBER,
                    order=1,
                    min_value=Decimal("10.000000"),
                    max_value=Decimal("1.000000"),
                )

    def test_question_option_order_must_start_at_one(self):
        question = Question.objects.create(
            form=self.form,
            text="Select",
            question_type=Question.QuestionType.SELECT,
            order=1,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                QuestionOption.objects.create(
                    question=question,
                    label="Invalid",
                    order=0,
                )

    def test_question_option_order_and_label_are_unique(self):
        question = Question.objects.create(
            form=self.form,
            text="Select",
            question_type=Question.QuestionType.SELECT,
            order=1,
        )
        QuestionOption.objects.create(
            question=question,
            label="One",
            order=1,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                QuestionOption.objects.create(
                    question=question,
                    label="Two",
                    order=1,
                )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                QuestionOption.objects.create(
                    question=question,
                    label="One",
                    order=2,
                )

    def test_answer_is_unique_per_submission_and_question(self):
        question = Question.objects.create(
            form=self.form,
            text="Text",
            question_type=Question.QuestionType.TEXT,
            order=1,
        )
        submission = FormSubmission.objects.create(
            form=self.form,
            respondent=self.user,
        )
        Answer.objects.create(
            submission=submission,
            question=question,
            text_value="first",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Answer.objects.create(
                    submission=submission,
                    question=question,
                    text_value="second",
                )

    def test_answer_option_pair_must_be_unique(self):
        question = Question.objects.create(
            form=self.form,
            text="Select",
            question_type=Question.QuestionType.SELECT,
            order=1,
        )
        option = QuestionOption.objects.create(
            question=question,
            label="One",
            order=1,
        )
        submission = FormSubmission.objects.create(
            form=self.form,
            respondent=self.user,
        )
        answer = Answer.objects.create(
            submission=submission,
            question=question,
        )
        AnswerOption.objects.create(answer=answer, option=option)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AnswerOption.objects.create(answer=answer, option=option)
