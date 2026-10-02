from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.participant_access import grant_participant_access
from apps.forms.models import Form, Question
from apps.processes.models import Process, ProcessRun, ProcessStepRun
from apps.processes.participant_selectors import RESOURCE_TYPE
from apps.processes.services import (
    close_process,
    create_process,
    create_process_step,
    publish_process,
)

User = get_user_model()


def _get_unlock_url(public_id):
    for name in ["unlock", "process-unlock", "process_unlock"]:
        try:
            return reverse(f"processes_participant_api:{name}", kwargs={"public_id": public_id})
        except Exception:
            pass
    raise ValueError(f"Could not resolve unlock url for {public_id}")


class ParticipantProcessExecutionAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="password123"
        )
        self.participant = User.objects.create_user(
            username="participant", email="part@example.com", password="password123"
        )

        # ساخت فرم‌های تستی به همراه سوالات
        self.form1 = Form.objects.create(
            owner=self.owner,
            title="Form Step 1",
            status=Form.Status.PUBLISHED,
        )
        self.q1 = Question.objects.create(
            form=self.form1,
            text="Your Name?",
            question_type=Question.QuestionType.TEXT,
            order=1,
            is_required=True,
        )

        self.form2 = Form.objects.create(
            owner=self.owner,
            title="Form Step 2",
            status=Form.Status.PUBLISHED,
        )
        self.q2 = Question.objects.create(
            form=self.form2,
            text="Your Age?",
            question_type=Question.QuestionType.NUMBER,
            order=1,
            is_required=True,
        )

        # ساخت پروسه Linear
        self.process = create_process(
            owner=self.owner,
            title="Onboarding Process",
            process_type=Process.ProcessType.LINEAR,
            visibility=Process.Visibility.PUBLIC,
        )
        self.step1 = create_process_step(
            process=self.process, owner=self.owner, form_id=self.form1.pk
        )
        self.step2 = create_process_step(
            process=self.process, owner=self.owner, form_id=self.form2.pk
        )
        publish_process(process=self.process, owner=self.owner)

    def test_anonymous_start_run_returns_resume_token(self):
        url = reverse(
            "processes_participant_api:run-start",
            kwargs={"public_id": self.process.public_id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()

        self.assertIn("resume_token", data)
        self.assertIsNotNone(data["resume_token"])
        self.assertEqual(len(data["steps"]), 2)
        self.assertEqual(data["steps"][0]["status"], ProcessStepRun.Status.AVAILABLE)
        self.assertEqual(data["steps"][1]["status"], ProcessStepRun.Status.LOCKED)

    def test_authenticated_start_run_assigns_respondent(self):
        self.client.force_login(self.participant)
        url = reverse(
            "processes_participant_api:run-start",
            kwargs={"public_id": self.process.public_id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()

        self.assertIsNone(data["resume_token"])
        run = ProcessRun.objects.get(public_id=data["public_id"])
        self.assertEqual(run.respondent, self.participant)

    def test_resume_anonymous_run_requires_x_resume_token_header(self):
        start_url = reverse(
            "processes_participant_api:run-start",
            kwargs={"public_id": self.process.public_id},
        )
        start_res = self.client.post(start_url)
        run_data = start_res.json()
        token = run_data["resume_token"]
        run_public_id = run_data["public_id"]

        detail_url = reverse(
            "processes_participant_api:run-detail",
            kwargs={
                "public_id": self.process.public_id,
                "run_public_id": run_public_id,
            },
        )

        # درخواست بدون هدر توکن باید با ۴۰۳ متوقف شود
        res_no_token = self.client.get(detail_url)
        self.assertEqual(res_no_token.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res_no_token.json()["error_code"], "INVALID_RESUME_TOKEN")

        # درخواست با توکن اشتباه باید ۴۰۳ بدهد
        res_wrong = self.client.get(detail_url, HTTP_X_RESUME_TOKEN="invalid-token")
        self.assertEqual(res_wrong.status_code, status.HTTP_403_FORBIDDEN)

        # درخواست با توکن صحیح run را با موفقیت برمی‌گرداند
        res_valid = self.client.get(detail_url, HTTP_X_RESUME_TOKEN=token)
        self.assertEqual(res_valid.status_code, status.HTTP_200_OK)
        self.assertEqual(res_valid.json()["public_id"], str(run_public_id))

    def test_complete_step_linear_progression(self):
        # 1. شروع اجرا
        start_url = reverse(
            "processes_participant_api:run-start",
            kwargs={"public_id": self.process.public_id},
        )
        start_res = self.client.post(start_url)
        token = start_res.json()["resume_token"]
        run_public_id = start_res.json()["public_id"]

        # 2. تلاش برای سابمیت استپ ۲ (که قفل است) باید ارور دهد
        step2_url = reverse(
            "processes_participant_api:step-complete",
            kwargs={
                "public_id": self.process.public_id,
                "run_public_id": run_public_id,
                "step_id": self.step2.pk,
            },
        )
        res_locked = self.client.post(
            step2_url,
            data={"answers": [{"question_id": self.q2.pk, "number_value": "25"}]},
            format="json",
            HTTP_X_RESUME_TOKEN=token,
        )
        self.assertEqual(res_locked.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. سابمیت موفق استپ ۱
        step1_url = reverse(
            "processes_participant_api:step-complete",
            kwargs={
                "public_id": self.process.public_id,
                "run_public_id": run_public_id,
                "step_id": self.step1.pk,
            },
        )
        res_step1 = self.client.post(
            step1_url,
            data={"answers": [{"question_id": self.q1.pk, "text_value": "Ali"}]},
            format="json",
            HTTP_X_RESUME_TOKEN=token,
        )
        self.assertEqual(res_step1.status_code, status.HTTP_200_OK)
        step1_data = res_step1.json()

        # استپ ۱ باید COMPLETED شده و استپ ۲ باید AVAILABLE شده باشد
        self.assertEqual(step1_data["steps"][0]["status"], ProcessStepRun.Status.COMPLETED)
        self.assertEqual(step1_data["steps"][1]["status"], ProcessStepRun.Status.AVAILABLE)
        self.assertEqual(step1_data["status"], ProcessRun.Status.IN_PROGRESS)

        # 4. سابمیت استپ ۲ و اتمام کل پروسه
        res_step2 = self.client.post(
            step2_url,
            data={"answers": [{"question_id": self.q2.pk, "number_value": "30"}]},
            format="json",
            HTTP_X_RESUME_TOKEN=token,
        )
        self.assertEqual(res_step2.status_code, status.HTTP_200_OK)
        final_data = res_step2.json()

        self.assertEqual(final_data["steps"][1]["status"], ProcessStepRun.Status.COMPLETED)
        self.assertEqual(final_data["status"], ProcessRun.Status.COMPLETED)
        self.assertIsNotNone(final_data["completed_at"])

    def test_private_process_requires_unlock_grant(self):
        priv_proc = create_process(
            owner=self.owner,
            title="Private Flow",
            process_type=Process.ProcessType.FREE,
            visibility=Process.Visibility.PRIVATE,
            access_password="SecretPass123",
        )
        create_process_step(process=priv_proc, owner=self.owner, form_id=self.form1.pk)
        publish_process(process=priv_proc, owner=self.owner)

        url = reverse(
            "processes_participant_api:run-start",
            kwargs={"public_id": priv_proc.public_id},
        )
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.json()["error_code"], "PARTICIPANT_ACCESS_REQUIRED")

        # اعطای دسترسی به سشن
        session = self.client.session
        grant_participant_access(
            session=session,
            resource_type=RESOURCE_TYPE,
            public_id=priv_proc.public_id,
        )
        session.save()

        res_granted = self.client.post(url)
        self.assertEqual(res_granted.status_code, status.HTTP_201_CREATED)

    def test_private_closed_process_fresh_session_unlock_and_resume(self):
        """تست رگرسیون: امکان آنلاک پروسه خصوصی CLOSED در سشن تازه و ادامه ران قبلی."""
        priv_proc = create_process(
            owner=self.owner,
            title="Private Closed Flow",
            process_type=Process.ProcessType.LINEAR,
            visibility=Process.Visibility.PRIVATE,
            access_password="SecretPass123",
        )
        priv_step = create_process_step(process=priv_proc, owner=self.owner, form_id=self.form1.pk)
        publish_process(process=priv_proc, owner=self.owner)

        unlock_url = _get_unlock_url(priv_proc.public_id)

        # 1. آنلاک و شروع ران
        unlock_res = self.client.post(unlock_url, data={"password": "SecretPass123"}, format="json")
        self.assertEqual(unlock_res.status_code, status.HTTP_204_NO_CONTENT)

        start_url = reverse(
            "processes_participant_api:run-start",
            kwargs={"public_id": priv_proc.public_id},
        )
        start_res = self.client.post(start_url)
        self.assertEqual(start_res.status_code, status.HTTP_201_CREATED)
        token = start_res.json()["resume_token"]
        run_public_id = start_res.json()["public_id"]

        # 2. بستن پروسه توسط مالک
        close_process(process=priv_proc, owner=self.owner)
        priv_proc.refresh_from_db()
        self.assertEqual(priv_proc.status, Process.Status.CLOSED)

        # 3. سشن تازه (بدون دسترسی/Grant قبلی)
        fresh_client = APIClient()
        detail_url = reverse(
            "processes_participant_api:run-detail",
            kwargs={
                "public_id": priv_proc.public_id,
                "run_public_id": run_public_id,
            },
        )

        # دسترسی بدون آنلاک با 403 متوقف می‌شود
        detail_no_grant = fresh_client.get(detail_url, HTTP_X_RESUME_TOKEN=token)
        self.assertEqual(detail_no_grant.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(detail_no_grant.json()["error_code"], "PARTICIPANT_ACCESS_REQUIRED")

        # تلاش برای شروع ران جدید روی پروسه CLOSED باید 404 بدهد
        start_closed_res = fresh_client.post(start_url)
        self.assertEqual(start_closed_res.status_code, status.HTTP_404_NOT_FOUND)

        # 4. آنلاک موفق پروسه CLOSED در سشن تازه با پسورد
        fresh_unlock = fresh_client.post(
            unlock_url, data={"password": "SecretPass123"}, format="json"
        )
        self.assertEqual(fresh_unlock.status_code, status.HTTP_204_NO_CONTENT)

        # 5. مشاهده موفق ران قبلی
        res_detail = fresh_client.get(detail_url, HTTP_X_RESUME_TOKEN=token)
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.json()["public_id"], str(run_public_id))

        # 6. تکمیل استپ در پروسه CLOSED با استفاده از priv_step معتبر
        step1_url = reverse(
            "processes_participant_api:step-complete",
            kwargs={
                "public_id": priv_proc.public_id,
                "run_public_id": run_public_id,
                "step_id": priv_step.pk,
            },
        )
        step_res = fresh_client.post(
            step1_url,
            data={"answers": [{"question_id": self.q1.pk, "text_value": "Resume Worked"}]},
            format="json",
            HTTP_X_RESUME_TOKEN=token,
        )
        self.assertEqual(step_res.status_code, status.HTTP_200_OK)
        self.assertEqual(step_res.json()["steps"][0]["status"], ProcessStepRun.Status.COMPLETED)

    def test_anonymous_run_resume_when_subsequently_authenticated(self):
        """تست رگرسیون: شرکت‌کننده‌ای که ران را ناشناس شروع کرده و بعداً لاگین می‌کند."""
        # 1. شروع ران ناشناس
        start_url = reverse(
            "processes_participant_api:run-start",
            kwargs={"public_id": self.process.public_id},
        )
        start_res = self.client.post(start_url)
        self.assertEqual(start_res.status_code, status.HTTP_201_CREATED)
        token = start_res.json()["resume_token"]
        run_public_id = start_res.json()["public_id"]

        # 2. کاربر بعداً لاگین می‌کند
        self.client.force_login(self.participant)

        # 3. مشاهده ران با توکن معتبر در حالت لاگین
        detail_url = reverse(
            "processes_participant_api:run-detail",
            kwargs={
                "public_id": self.process.public_id,
                "run_public_id": run_public_id,
            },
        )
        detail_res = self.client.get(detail_url, HTTP_X_RESUME_TOKEN=token)
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)

        # 4. تکمیل استپ با توکن معتبر نباید ارور Identity Mismatch بدهد
        step1_url = reverse(
            "processes_participant_api:step-complete",
            kwargs={
                "public_id": self.process.public_id,
                "run_public_id": run_public_id,
                "step_id": self.step1.pk,
            },
        )
        res_step = self.client.post(
            step1_url,
            data={"answers": [{"question_id": self.q1.pk, "text_value": "Auth Anon"}]},
            format="json",
            HTTP_X_RESUME_TOKEN=token,
        )
        self.assertEqual(res_step.status_code, status.HTTP_200_OK)

        # سابمیشن ثبت‌شده باید همچنان ناشناس (None) باشد
        step_run = ProcessStepRun.objects.get(
            process_run__public_id=run_public_id, process_step=self.step1
        )
        self.assertEqual(step_run.status, ProcessStepRun.Status.COMPLETED)
        self.assertIsNone(step_run.submission.respondent)
