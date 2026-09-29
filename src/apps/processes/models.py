import uuid

from django.conf import settings
from django.db import models


class Process(models.Model):
    class ProcessType(models.TextChoices):
        LINEAR = "LINEAR", "Linear"
        FREE = "FREE", "Free"

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
        related_name="owned_processes",
    )
    category = models.ForeignKey(
        "core.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processes",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    process_type = models.CharField(
        max_length=10,
        choices=ProcessType.choices,
    )
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
                name="proc_owner_status_created_idx",
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
                name="process_visibility_password_ck",
            ),
        ]

    def __str__(self):
        return f"Process {self.pk} - {self.title}"


class ProcessStep(models.Model):
    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    form = models.ForeignKey(
        "forms.Form",
        on_delete=models.PROTECT,
        related_name="process_steps",
    )
    order = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["process", "order"],
                name="process_step_order_uniq",
            ),
            models.UniqueConstraint(
                fields=["process", "form"],
                name="process_step_form_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(order__gte=1),
                name="process_step_order_gte_1_ck",
            ),
        ]

    def __str__(self):
        return f"Step {self.order} for Process {self.process_id}"


class ProcessRun(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    process = models.ForeignKey(
        Process,
        on_delete=models.PROTECT,
        related_name="runs",
    )
    respondent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="process_runs",
    )
    resume_token_hash = models.CharField(
        max_length=128,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["process", "status", "-started_at"],
                name="proc_run_status_started_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        respondent__isnull=False,
                        resume_token_hash__isnull=True,
                    )
                    | models.Q(
                        respondent__isnull=True,
                        resume_token_hash__isnull=False,
                    )
                ),
                name="proc_run_identity_xor_ck",
            ),
            models.UniqueConstraint(
                fields=["resume_token_hash"],
                condition=models.Q(resume_token_hash__isnull=False),
                name="proc_run_token_hash_uniq",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="IN_PROGRESS",
                        completed_at__isnull=True,
                    )
                    | models.Q(
                        status="COMPLETED",
                        completed_at__isnull=False,
                    )
                ),
                name="proc_run_status_completed_ck",
            ),
        ]

    def __str__(self):
        return f"Run {self.pk} - {self.process.title}"


class ProcessStepRun(models.Model):
    class Status(models.TextChoices):
        LOCKED = "LOCKED", "Locked"
        AVAILABLE = "AVAILABLE", "Available"
        COMPLETED = "COMPLETED", "Completed"

    process_run = models.ForeignKey(
        ProcessRun,
        on_delete=models.CASCADE,
        related_name="step_runs",
    )
    process_step = models.ForeignKey(
        ProcessStep,
        on_delete=models.PROTECT,
        related_name="run_states",
    )
    # تغییر به OneToOneField جهت تطابق با تست دیتابیس و جلوگیری از تعلق یک سابمیت به چند استپ‌ران
    submission = models.OneToOneField(
        "forms.FormSubmission",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="process_step_run",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.LOCKED,
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["process_run", "status"],
                name="step_run_run_status_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["process_run", "process_step"],
                name="step_run_run_step_uniq",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="COMPLETED",
                        submission__isnull=False,
                        completed_at__isnull=False,
                    )
                    | models.Q(
                        status__in=["LOCKED", "AVAILABLE"],
                        submission__isnull=True,
                        completed_at__isnull=True,
                    )
                ),
                name="step_run_state_data_ck",
            ),
        ]

    def __str__(self):
        return f"StepRun {self.pk} ({self.status}) for Run {self.process_run_id}"
