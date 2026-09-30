from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.forms.models import Form
from apps.processes.models import Process, ProcessRun, ProcessStepRun
from apps.processes.participant_selectors import (
    get_executable_process_by_public_id,
    get_in_progress_process_run_for_respondent,
    get_process_run_by_token_hash,
    get_process_run_for_process,
)
from apps.processes.services import (
    close_process,
    complete_process_step_run,
    create_process,
    create_process_step,
    publish_process,
    start_process_run,
)

User = get_user_model()


class ProcessExecutionServicesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner", email="owner@example.com", password="password123"
        )
        self.other_user = User.objects.create_user(
            username="other", email="other@example.com", password="password123"
        )

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

    def test_free_process_execution_arbitrary_order_and_completion(self):
        """تست پروسه FREE: همه استپ‌ها در ابتدا AVAILABLE هستند و بدون ترتیب تکمیل می‌شوند."""
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

        self.assertEqual(step_runs[step1.pk].status, ProcessStepRun.Status.AVAILABLE)
        self.assertEqual(step_runs[step2.pk].status, ProcessStepRun.Status.AVAILABLE)

        complete_process_step_run(
            process_run=run,
            step_run_id=step_runs[step2.pk].pk,
            answers=[],
            respondent=self.user,
        )
        run.refresh_from_db()
        self.assertEqual(run.status, ProcessRun.Status.IN_PROGRESS)
        self.assertIsNone(run.completed_at)

        complete_process_step_run(
            process_run=run,
            step_run_id=step_runs[step1.pk].pk,
            answers=[],
            respondent=self.user,
        )
        run.refresh_from_db()
        self.assertEqual(run.status, ProcessRun.Status.COMPLETED)
        self.assertIsNotNone(run.completed_at)

    def test_invariants_enforcement_in_step_completion(self):
        """تست بررسی اینواریانت‌های سرویس و جلوگیری از دابل‌سابمیشن."""
        proc = create_process(
            owner=self.user,
            title="Invariant Test",
            process_type=Process.ProcessType.LINEAR,
        )
        step = create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        publish_process(process=proc, owner=self.user)

        run, _ = start_process_run(process=proc, respondent=self.user)
        step_run = run.step_runs.first()

        completed_step_run = complete_process_step_run(
            process_run=run,
            step_run_id=step_run.pk,
            answers=[],
            respondent=self.user,
        )
        self.assertEqual(completed_step_run.status, ProcessStepRun.Status.COMPLETED)

        # رد تکمیل مجدد
        with self.assertRaises(ValidationError) as ctx:
            complete_process_step_run(
                process_run=run,
                step_run_id=step_run.pk,
                answers=[],
                respondent=self.user,
            )
        self.assertIn("run", ctx.exception.message_dict)

        # رد استپ متعلق به پروسه دیگر
        other_proc = create_process(
            owner=self.user,
            title="Other Process",
            process_type=Process.ProcessType.LINEAR,
        )
        create_process_step(process=other_proc, owner=self.user, form_id=self.form2.pk)
        publish_process(process=other_proc, owner=self.user)
        other_run, _ = start_process_run(process=other_proc, respondent=self.user)
        other_step_run = other_run.step_runs.first()

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

        # رد سابمیشنی با form_id نامطابق
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

    def test_authoritative_respondent_enforcement(self):
        """تست تأیید هویت Authoritative: جلوگیری از جعل respondent (الزام تیم‌لید در بلاکر ۳)."""
        proc = create_process(
            owner=self.user,
            title="Authoritative Respondent Test",
            process_type=Process.ProcessType.LINEAR,
        )
        create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        publish_process(process=proc, owner=self.user)

        # 1. ران احراز هویت شده با کاربر اصلی، اگر کالبک کاربری دیگر بفرستد رد می‌شود
        run_auth, _ = start_process_run(process=proc, respondent=self.user)
        step_run_auth = run_auth.step_runs.first()

        with self.assertRaises(ValidationError) as ctx:
            complete_process_step_run(
                process_run=run_auth,
                step_run_id=step_run_auth.pk,
                answers=[],
                respondent=self.other_user,
            )
        self.assertIn("respondent", ctx.exception.message_dict)

        # 2. ران ناشناس (Anonymous)، اگر کالبک کاربر احرازشده بفرستد رد می‌شود
        run_anon, _ = start_process_run(process=proc, respondent=None)
        step_run_anon = run_anon.step_runs.first()

        with self.assertRaises(ValidationError) as ctx:
            complete_process_step_run(
                process_run=run_anon,
                step_run_id=step_run_anon.pk,
                answers=[],
                respondent=self.user,
            )
        self.assertIn("respondent", ctx.exception.message_dict)

        # 3. ثبت سابمیشن برای ران احراز هویت شده همیشه با هویت معتبر ProcessRun انجام می‌شود
        completed_auth = complete_process_step_run(
            process_run=run_auth,
            step_run_id=step_run_auth.pk,
            answers=[],
            respondent=self.user,
        )
        self.assertEqual(completed_auth.submission.respondent, self.user)

        # 4. ثبت سابمیشن برای ران ناشناس همواره بدون هویت (None) انجام می‌شود
        completed_anon = complete_process_step_run(
            process_run=run_anon,
            step_run_id=step_run_anon.pk,
            answers=[],
        )
        self.assertIsNone(completed_anon.submission.respondent)

    def test_closed_process_rejects_new_run(self):
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
        proc = create_process(
            owner=self.user,
            title="Form Closes Later",
            process_type=Process.ProcessType.LINEAR,
        )
        create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        publish_process(process=proc, owner=self.user)

        run, _ = start_process_run(process=proc, respondent=self.user)
        step_run = run.step_runs.first()

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


class ParticipantSelectorsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner", email="owner@example.com", password="password123"
        )
        self.other_user = User.objects.create_user(
            username="other", email="other@example.com", password="password123"
        )
        self.form = Form.objects.create(
            owner=self.user, title="Form 1", status=Form.Status.PUBLISHED
        )
        self.process = create_process(
            owner=self.user,
            title="Test Process",
            process_type=Process.ProcessType.LINEAR,
        )
        create_process_step(process=self.process, owner=self.user, form_id=self.form.pk)
        publish_process(process=self.process, owner=self.user)

    def test_get_executable_process_by_public_id(self):
        # پروسه PUBLISHED قابل اجرا و دسترسی است
        self.assertIsNotNone(get_executable_process_by_public_id(public_id=self.process.public_id))

        # پروسه CLOSED نیز برای ادامه اجرای ران‌های قبلی قابل بازیابی است
        close_process(process=self.process, owner=self.user)
        self.assertIsNotNone(get_executable_process_by_public_id(public_id=self.process.public_id))

        # پروسه DRAFT هرگز بازگردانده نمی‌شود
        draft = create_process(
            owner=self.user,
            title="Draft",
            process_type=Process.ProcessType.LINEAR,
        )
        self.assertIsNone(get_executable_process_by_public_id(public_id=draft.public_id))

    def test_get_process_run_for_process(self):
        run, _ = start_process_run(process=self.process, respondent=self.user)
        found = get_process_run_for_process(process=self.process, run_public_id=run.public_id)
        self.assertEqual(found, run)

        # بررسی اسکوپ پروسه: اگر متعلق به پروسه دیگری باشد None برمی‌گرداند
        other_proc = create_process(
            owner=self.user,
            title="Other Proc",
            process_type=Process.ProcessType.LINEAR,
        )
        create_process_step(process=other_proc, owner=self.user, form_id=self.form.pk)
        publish_process(process=other_proc, owner=self.user)
        self.assertIsNone(
            get_process_run_for_process(process=other_proc, run_public_id=run.public_id)
        )

    def test_get_in_progress_process_run_for_respondent(self):
        run, _ = start_process_run(process=self.process, respondent=self.user)
        found = get_in_progress_process_run_for_respondent(
            process=self.process, respondent=self.user
        )
        self.assertEqual(found, run)

        # کاربر دیگر نمی‌تواند ران این کاربر را ببیند
        self.assertIsNone(
            get_in_progress_process_run_for_respondent(
                process=self.process, respondent=self.other_user
            )
        )

        # برای کاربر ناشناس None برمی‌گرداند
        self.assertIsNone(
            get_in_progress_process_run_for_respondent(process=self.process, respondent=None)
        )

    def test_get_process_run_by_token_hash(self):
        run, raw_token = start_process_run(process=self.process, respondent=None)
        found = get_process_run_by_token_hash(
            process=self.process, resume_token_hash=run.resume_token_hash
        )
        self.assertEqual(found, run)

        # برای هش نامعتبر یا خالی None برمی‌گرداند
        self.assertIsNone(
            get_process_run_by_token_hash(process=self.process, resume_token_hash="invalid_hash")
        )
        self.assertIsNone(
            get_process_run_by_token_hash(process=self.process, resume_token_hash=None)
        )
