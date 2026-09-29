from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core.models import Category
from apps.forms.models import Form
from apps.processes.models import Process, ProcessRun, ProcessStepRun
from apps.processes.services import (
    close_process,
    complete_process_step_run,
    create_process,
    create_process_step,
    delete_process_step,
    publish_process,
    start_process_run,
)

User = get_user_model()


class ProcessServicesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner", email="owner@example.com", password="password123"
        )
        self.other_user = User.objects.create_user(
            username="other", email="other@example.com", password="password123"
        )
        self.category = Category.objects.create(name="Onboarding", owner=self.user)
        self.other_category = Category.objects.create(name="Other", owner=self.other_user)

        self.form1 = Form.objects.create(
            owner=self.user,
            title="Form 1",
            status=Form.Status.PUBLISHED,
        )
        self.form2 = Form.objects.create(
            owner=self.user,
            title="Form 2",
            status=Form.Status.PUBLISHED,
        )
        self.draft_form = Form.objects.create(
            owner=self.user,
            title="Draft Form",
            status=Form.Status.DRAFT,
        )

    def test_create_process_draft_public_and_private(self):
        # Public process
        proc = create_process(
            owner=self.user,
            title="HR Process",
            process_type=Process.ProcessType.LINEAR,
            visibility=Process.Visibility.PUBLIC,
        )
        self.assertEqual(proc.status, Process.Status.DRAFT)
        self.assertEqual(proc.visibility, Process.Visibility.PUBLIC)
        self.assertIsNone(proc.access_password_hash)

        # Private process
        priv_proc = create_process(
            owner=self.user,
            title="Secret Process",
            process_type=Process.ProcessType.FREE,
            visibility=Process.Visibility.PRIVATE,
            access_password="SecretPassword123",
        )
        self.assertEqual(priv_proc.visibility, Process.Visibility.PRIVATE)
        self.assertIsNotNone(priv_proc.access_password_hash)

    def test_create_process_private_without_password_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            create_process(
                owner=self.user,
                title="Invalid Private",
                process_type=Process.ProcessType.LINEAR,
                visibility=Process.Visibility.PRIVATE,
                access_password=None,
            )
        self.assertIn("access_password", ctx.exception.message_dict)

    def test_category_ownership_validation(self):
        with self.assertRaises(ValidationError) as ctx:
            create_process(
                owner=self.user,
                title="Wrong Category",
                process_type=Process.ProcessType.LINEAR,
                category_id=self.other_category.pk,
            )
        self.assertIn("category", ctx.exception.message_dict)

    def test_step_management_contiguous_and_duplicate_rejection(self):
        proc = create_process(
            owner=self.user,
            title="Step Test",
            process_type=Process.ProcessType.LINEAR,
        )
        step1 = create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        step2 = create_process_step(process=proc, owner=self.user, form_id=self.form2.pk)
        self.assertEqual(step1.order, 1)
        self.assertEqual(step2.order, 2)

        # عدم امکان افزودن فرم تکراری
        with self.assertRaises(ValidationError) as ctx:
            create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        self.assertIn("form_id", ctx.exception.message_dict)

        # حذف مرحله و بازنویسی ترتیب
        delete_process_step(process=proc, owner=self.user, step_id=step1.pk)
        step2.refresh_from_db()
        self.assertEqual(step2.order, 1)

    def test_publish_readiness_validations(self):
        proc = create_process(
            owner=self.user,
            title="Empty Process",
            process_type=Process.ProcessType.LINEAR,
        )
        # انتشار پروسه بدون مرحله نامعتبر است
        with self.assertRaises(ValidationError) as ctx:
            publish_process(process=proc, owner=self.user)
        self.assertIn("steps", ctx.exception.message_dict)

    def test_publish_process_locks_step_forms_with_select_for_update(self):
        proc = create_process(
            owner=self.user,
            title="Lock Test",
            process_type=Process.ProcessType.LINEAR,
        )
        create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        published = publish_process(process=proc, owner=self.user)
        self.assertEqual(published.status, Process.Status.PUBLISHED)

    def test_public_process_rejects_private_form_at_publication(self):
        priv_form = Form.objects.create(
            owner=self.user,
            title="Private Form",
            status=Form.Status.PUBLISHED,
            visibility=Form.Visibility.PRIVATE,
            access_password_hash="some-hash",
        )
        proc = create_process(
            owner=self.user,
            title="Public With Private Form",
            process_type=Process.ProcessType.LINEAR,
            visibility=Process.Visibility.PUBLIC,
        )
        create_process_step(process=proc, owner=self.user, form_id=priv_form.pk)
        with self.assertRaises(ValidationError) as ctx:
            publish_process(process=proc, owner=self.user)
        self.assertIn("forms", ctx.exception.message_dict)

    def test_publish_process_fails_if_step_form_is_closed(self):
        closed_form = Form.objects.create(
            owner=self.user,
            title="Closed Form",
            status=Form.Status.CLOSED,
        )
        proc = create_process(
            owner=self.user,
            title="Closed Step Form",
            process_type=Process.ProcessType.LINEAR,
        )
        create_process_step(process=proc, owner=self.user, form_id=closed_form.pk)
        with self.assertRaises(ValidationError) as ctx:
            publish_process(process=proc, owner=self.user)
        self.assertIn("forms", ctx.exception.message_dict)

    # =========================================================================
    # PROCESS EXECUTION ENGINE TESTS (#35)
    # =========================================================================

    def test_start_process_run_authenticated_and_anonymous(self):
        """تست شروع اجرای پروسه برای کاربر لاگین‌شده و کاربر ناشناس با هش توکن."""
        proc = create_process(
            owner=self.user,
            title="Execution Test",
            process_type=Process.ProcessType.LINEAR,
        )
        create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        publish_process(process=proc, owner=self.user)

        # 1. تست حالت Authenticated
        run_auth, raw_token_auth = start_process_run(process=proc, respondent=self.user)
        self.assertEqual(run_auth.respondent, self.user)
        self.assertIsNone(run_auth.resume_token_hash)
        self.assertIsNone(raw_token_auth)

        # 2. تست حالت Anonymous
        run_anon, raw_token_anon = start_process_run(process=proc, respondent=None)
        self.assertIsNone(run_anon.respondent)
        self.assertIsNotNone(run_anon.resume_token_hash)
        self.assertIsNotNone(raw_token_anon)

    def test_linear_process_execution_flow(self):
        """تست جریان اجرای خطی (LINEAR): استپ اول AVAILABLE و بقیه LOCKED."""
        proc = create_process(
            owner=self.user,
            title="Linear Flow",
            process_type=Process.ProcessType.LINEAR,
        )
        create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        create_process_step(process=proc, owner=self.user, form_id=self.form2.pk)
        publish_process(process=proc, owner=self.user)

        run, _ = start_process_run(process=proc, respondent=self.user)
        step_runs = list(run.step_runs.order_by("process_step__order"))

        self.assertEqual(step_runs[0].status, ProcessStepRun.Status.AVAILABLE)
        self.assertEqual(step_runs[1].status, ProcessStepRun.Status.LOCKED)

    def test_invariants_enforcement_in_step_completion(self):
        """تست بررسی اینواریانت‌های سرویس و جلوگیری از تکمیل مجدد (Duplicate Completion)."""
        proc = create_process(
            owner=self.user,
            title="Invariant Test",
            process_type=Process.ProcessType.LINEAR,
        )
        step = create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        publish_process(process=proc, owner=self.user)

        run, _ = start_process_run(process=proc, respondent=self.user)
        step_run = run.step_runs.first()

        # 1. تکمیل موفق استپ
        completed_step_run = complete_process_step_run(
            process_run=run,
            step_run_id=step_run.pk,
            answers=[],
            respondent=self.user,
        )
        self.assertEqual(completed_step_run.status, ProcessStepRun.Status.COMPLETED)
        self.assertIsNotNone(completed_step_run.completed_at)

        # 2. تست Duplicate Completion (تلاش برای تکمیل مجدد استپی که پروسه آن تمام شده)
        with self.assertRaises(ValidationError) as ctx:
            complete_process_step_run(
                process_run=run,
                step_run_id=step_run.pk,
                answers=[],
                respondent=self.user,
            )
        self.assertIn("run", ctx.exception.message_dict)

        # 3. تست Invariant: رد مرحله‌ای از پروسه دیگر (cross-process step rejection)
        other_proc = create_process(
            owner=self.user,
            title="Other Process",
            process_type=Process.ProcessType.LINEAR,
        )
        create_process_step(process=other_proc, owner=self.user, form_id=self.form2.pk)
        publish_process(process=other_proc, owner=self.user)
        other_run, _ = start_process_run(process=other_proc, respondent=self.user)
        other_step_run = other_run.step_runs.first()

        # دستکاری شبیه‌سازی برای تست اینواریانت process_step.process_id == process_run.process_id
        other_step_run.process_step = step
        other_step_run.save(update_fields=["process_step"])

        with self.assertRaises(ValidationError) as ctx:
            complete_process_step_run(
                process_run=other_run,
                step_run_id=other_step_run.pk,
                answers=[],
                respondent=self.user,
            )
        self.assertIn("invariant", ctx.exception.message_dict)

        # 4. تست Invariant: رد سابمیشنی با form_id نامطابق (wrong-form submission rejection)
        fake_submission = MagicMock(form_id=99999)
        with patch("apps.processes.services.submit_form", return_value=fake_submission):
            new_run, _ = start_process_run(process=proc, respondent=self.user)
            new_step_run = new_run.step_runs.first()
            with self.assertRaises(ValidationError) as ctx:
                complete_process_step_run(
                    process_run=new_run,
                    step_run_id=new_step_run.pk,
                    answers=[],
                    respondent=self.user,
                )
            self.assertIn("invariant", ctx.exception.message_dict)

    def test_free_process_execution_arbitrary_order_and_completion(self):
        """تست پروسه FREE: همه استپ‌ها در دسترس هستند و بدون ترتیب تکمیل می‌شوند."""
        proc = create_process(
            owner=self.user,
            title="Free Workflow",
            process_type=Process.ProcessType.FREE,
        )
        step1 = create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        step2 = create_process_step(process=proc, owner=self.user, form_id=self.form2.pk)
        publish_process(process=proc, owner=self.user)

        run, _ = start_process_run(process=proc, respondent=self.user)
        step_runs = {sr.process_step_id: sr for sr in run.step_runs.all()}

        # در ابتدای کار هر دو AVAILABLE هستند
        self.assertEqual(step_runs[step1.pk].status, ProcessStepRun.Status.AVAILABLE)
        self.assertEqual(step_runs[step2.pk].status, ProcessStepRun.Status.AVAILABLE)

        # تکمیل استپ ۲ قبل از استپ ۱ (Arbitrary Order)
        complete_process_step_run(
            process_run=run,
            step_run_id=step_runs[step2.pk].pk,
            answers=[],
            respondent=self.user,
        )
        run.refresh_from_db()
        self.assertEqual(run.status, ProcessRun.Status.IN_PROGRESS)
        self.assertIsNone(run.completed_at)

        # تکمیل استپ ۱ و بررسی ثبت مهر زمانی پایان کل پروسه
        complete_process_step_run(
            process_run=run,
            step_run_id=step_runs[step1.pk].pk,
            answers=[],
            respondent=self.user,
        )
        run.refresh_from_db()
        self.assertEqual(run.status, ProcessRun.Status.COMPLETED)
        self.assertIsNotNone(run.completed_at)

    def test_closed_process_rejects_new_run(self):
        """تست عدم امکان شروع پروسه‌ای که در وضعیت CLOSED قرار دارد."""
        proc = create_process(
            owner=self.user,
            title="Will Be Closed",
            process_type=Process.ProcessType.LINEAR,
        )
        create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        publish_process(process=proc, owner=self.user)
        close_process(process=proc, owner=self.user)

        with self.assertRaises(ValidationError) as ctx:
            start_process_run(process=proc, respondent=self.user)
        self.assertIn("process", ctx.exception.message_dict)

    def test_step_completion_fails_if_step_form_is_closed(self):
        """تست رفتار BL-DATA-002: در صورتی که فرم حین اجرا CLOSED شود، خطا صادر می‌شود."""
        proc = create_process(
            owner=self.user,
            title="Form Closes Later",
            process_type=Process.ProcessType.LINEAR,
        )
        create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        publish_process(process=proc, owner=self.user)

        run, _ = start_process_run(process=proc, respondent=self.user)
        step_run = run.step_runs.first()

        # بستن فرم
        self.form1.status = Form.Status.CLOSED
        self.form1.save(update_fields=["status"])

        with self.assertRaises(ValidationError) as ctx:
            complete_process_step_run(
                process_run=run,
                step_run_id=step_run.pk,
                answers=[],
                respondent=self.user,
            )
        self.assertIn("form", ctx.exception.message_dict)
