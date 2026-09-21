from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.forms.models import Form, FormSubmission
from apps.processes.models import Process, ProcessRun, ProcessStep, ProcessStepRun


class ProcessDatabaseConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="process-owner",
            email="process-owner@example.com",
            password="test-password",
        )
        self.form = Form.objects.create(
            owner=self.user,
            title="Process Form",
            visibility=Form.Visibility.PUBLIC,
            status=Form.Status.PUBLISHED,
        )
        self.process = Process.objects.create(
            owner=self.user,
            title="Constraint Process",
            process_type=Process.ProcessType.LINEAR,
            visibility=Process.Visibility.PUBLIC,
            status=Process.Status.PUBLISHED,
        )
        self.step = ProcessStep.objects.create(
            process=self.process,
            form=self.form,
            order=1,
        )

    def test_private_process_requires_password_hash(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Process.objects.create(
                    owner=self.user,
                    title="Private without password",
                    process_type=Process.ProcessType.FREE,
                    visibility=Process.Visibility.PRIVATE,
                    access_password_hash=None,
                )

    def test_process_step_order_must_start_at_one(self):
        second_form = Form.objects.create(
            owner=self.user,
            title="Second Form",
            visibility=Form.Visibility.PUBLIC,
            status=Form.Status.PUBLISHED,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProcessStep.objects.create(
                    process=self.process,
                    form=second_form,
                    order=0,
                )

    def test_process_step_order_and_form_are_unique_per_process(self):
        second_form = Form.objects.create(
            owner=self.user,
            title="Second Form",
            visibility=Form.Visibility.PUBLIC,
            status=Form.Status.PUBLISHED,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProcessStep.objects.create(
                    process=self.process,
                    form=second_form,
                    order=1,
                )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProcessStep.objects.create(
                    process=self.process,
                    form=self.form,
                    order=2,
                )

    def test_process_run_requires_exactly_one_identity(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProcessRun.objects.create(process=self.process)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProcessRun.objects.create(
                    process=self.process,
                    respondent=self.user,
                    resume_token_hash="both-identities",
                )

    def test_non_null_resume_token_hash_must_be_unique(self):
        ProcessRun.objects.create(
            process=self.process,
            resume_token_hash="same-token-digest",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProcessRun.objects.create(
                    process=self.process,
                    resume_token_hash="same-token-digest",
                )

    def test_process_run_status_and_completed_at_must_match(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProcessRun.objects.create(
                    process=self.process,
                    respondent=self.user,
                    status=ProcessRun.Status.COMPLETED,
                    completed_at=None,
                )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProcessRun.objects.create(
                    process=self.process,
                    resume_token_hash="invalid-status-token",
                    status=ProcessRun.Status.IN_PROGRESS,
                    completed_at=timezone.now(),
                )

    def test_process_step_run_pair_must_be_unique(self):
        run = ProcessRun.objects.create(
            process=self.process,
            respondent=self.user,
        )
        ProcessStepRun.objects.create(
            process_run=run,
            process_step=self.step,
            status=ProcessStepRun.Status.AVAILABLE,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProcessStepRun.objects.create(
                    process_run=run,
                    process_step=self.step,
                    status=ProcessStepRun.Status.AVAILABLE,
                )

    def test_process_step_run_state_data_must_match(self):
        run = ProcessRun.objects.create(
            process=self.process,
            respondent=self.user,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProcessStepRun.objects.create(
                    process_run=run,
                    process_step=self.step,
                    status=ProcessStepRun.Status.COMPLETED,
                    submission=None,
                    completed_at=None,
                )

    def test_submission_can_belong_to_only_one_process_step_run(self):
        submission = FormSubmission.objects.create(
            form=self.form,
            respondent=self.user,
        )
        run_one = ProcessRun.objects.create(
            process=self.process,
            respondent=self.user,
        )
        run_two = ProcessRun.objects.create(
            process=self.process,
            respondent=self.user,
        )

        ProcessStepRun.objects.create(
            process_run=run_one,
            process_step=self.step,
            submission=submission,
            status=ProcessStepRun.Status.COMPLETED,
            completed_at=timezone.now(),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProcessStepRun.objects.create(
                    process_run=run_two,
                    process_step=self.step,
                    submission=submission,
                    status=ProcessStepRun.Status.COMPLETED,
                    completed_at=timezone.now(),
                )

    def test_valid_authenticated_and_anonymous_runs_are_allowed(self):
        authenticated = ProcessRun.objects.create(
            process=self.process,
            respondent=self.user,
        )
        anonymous = ProcessRun.objects.create(
            process=self.process,
            resume_token_hash="unique-anonymous-token",
        )

        self.assertIsNotNone(authenticated.pk)
        self.assertIsNotNone(anonymous.pk)
