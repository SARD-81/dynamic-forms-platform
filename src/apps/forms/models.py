import uuid

from django.conf import settings
from django.db import models

POSITIVE_INTEGER_MAX = 2_147_483_647


class Form(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "PUBLIC", "Public"
        PRIVATE = "PRIVATE", "Private"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        CLOSED = "CLOSED", "Closed"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_forms",
    )
    category = models.ForeignKey(
        "core.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="forms",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    access_password_hash = models.CharField(
        max_length=128,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    view_count = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["owner", "status", "-created_at"],
                name="form_owner_status_created_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        visibility="PUBLIC",
                        access_password_hash__isnull=True,
                    )
                    | models.Q(
                        visibility="PRIVATE",
                        access_password_hash__isnull=False,
                    )
                ),
                name="form_visibility_password_ck",
            ),
        ]


class Question(models.Model):
    class QuestionType(models.TextChoices):
        TEXT = "TEXT", "Text"
        NUMBER = "NUMBER", "Number"
        SELECT = "SELECT", "Select"
        CHECKBOX = "CHECKBOX", "Checkbox"

    form = models.ForeignKey(
        Form,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    text = models.TextField()
    question_type = models.CharField(
        max_length=16,
        choices=QuestionType.choices,
    )
    is_required = models.BooleanField(default=False)
    order = models.PositiveIntegerField()
    max_length = models.PositiveIntegerField(null=True, blank=True)
    min_value = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        null=True,
        blank=True,
    )
    max_value = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["form", "order"],
                name="question_form_order_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(order__gte=1),
                name="question_order_gte_1_ck",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(min_value__isnull=True)
                    | models.Q(max_value__isnull=True)
                    | models.Q(min_value__lte=models.F("max_value"))
                ),
                name="question_numeric_bounds_ck",
            ),
        ]


class QuestionOption(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options",
    )
    label = models.CharField(max_length=255)
    order = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["question", "order"],
                name="question_option_order_uniq",
            ),
            models.UniqueConstraint(
                fields=["question", "label"],
                name="question_option_label_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(order__gte=1),
                name="question_option_order_gte_1_ck",
            ),
        ]


class FormSubmission(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    form = models.ForeignKey(
        Form,
        on_delete=models.PROTECT,
        related_name="submissions",
    )
    respondent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_submissions",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["form", "-submitted_at"],
                name="formsub_form_submitted_idx",
            ),
        ]


class Answer(models.Model):
    submission = models.ForeignKey(
        FormSubmission,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,
        related_name="answers",
    )
    text_value = models.TextField(null=True, blank=True)
    number_value = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "question"],
                name="answer_submission_question_uniq",
            ),
        ]


class AnswerOption(models.Model):
    answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        related_name="selected_options",
    )
    option = models.ForeignKey(
        QuestionOption,
        on_delete=models.PROTECT,
        related_name="answer_links",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["answer", "option"],
                name="answer_option_pair_uniq",
            ),
        ]
