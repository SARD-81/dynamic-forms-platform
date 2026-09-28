from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.forms.models import Form
from apps.processes.models import Process, ProcessStep

User = get_user_model()


class ProcessAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="password123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

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

    def test_unauthenticated_requests_return_403(self):
        anon_client = APIClient()
        response = anon_client.get("/api/v1/processes/")
        self.assertEqual(response.status_code, 403)

    def test_create_and_list_process(self):
        payload = {
            "title": "Onboarding Process",
            "process_type": "LINEAR",
            "visibility": "PUBLIC",
            "description": "Welcome guide",
        }
        response = self.client.post("/api/v1/processes/", data=payload, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["title"], "Onboarding Process")
        self.assertEqual(data["process_type"], "LINEAR")
        self.assertNotIn("access_password_hash", data)

        list_resp = self.client.get("/api/v1/processes/")
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(len(list_resp.json()), 1)

    def test_step_crud_and_reorder_via_api(self):
        proc_resp = self.client.post(
            "/api/v1/processes/",
            data={"title": "Main Flow", "process_type": "FREE"},
            format="json",
        )
        proc_id = proc_resp.json()["id"]

        # Add Step 1
        s1_resp = self.client.post(
            f"/api/v1/processes/{proc_id}/steps/",
            data={"form_id": self.form1.pk},
            format="json",
        )
        self.assertEqual(s1_resp.status_code, 201)
        s1_id = s1_resp.json()["id"]

        # Add Step 2
        s2_resp = self.client.post(
            f"/api/v1/processes/{proc_id}/steps/",
            data={"form_id": self.form2.pk},
            format="json",
        )
        self.assertEqual(s2_resp.status_code, 201)
        s2_id = s2_resp.json()["id"]

        # Reorder
        reorder_resp = self.client.post(
            f"/api/v1/processes/{proc_id}/steps/reorder/",
            data={"step_ids": [s2_id, s1_id]},
            format="json",
        )
        self.assertEqual(reorder_resp.status_code, 200)
        self.assertEqual(reorder_resp.json()[0]["id"], s2_id)
        self.assertEqual(reorder_resp.json()[0]["order"], 1)

    def test_publish_and_close_endpoints(self):
        proc_resp = self.client.post(
            "/api/v1/processes/",
            data={"title": "Publish Me", "process_type": "LINEAR"},
            format="json",
        )
        proc_id = proc_resp.json()["id"]

        # Publish without step fails
        fail_pub = self.client.post(f"/api/v1/processes/{proc_id}/publish/")
        self.assertEqual(fail_pub.status_code, 400)
        self.assertEqual(fail_pub.json()["error_code"], "PROCESS_VALIDATION_ERROR")

        # Add step and publish
        self.client.post(
            f"/api/v1/processes/{proc_id}/steps/",
            data={"form_id": self.form1.pk},
            format="json",
        )
        pub_resp = self.client.post(f"/api/v1/processes/{proc_id}/publish/")
        self.assertEqual(pub_resp.status_code, 200)
        self.assertEqual(pub_resp.json()["status"], "PUBLISHED")

        # Close
        close_resp = self.client.post(f"/api/v1/processes/{proc_id}/close/")
        self.assertEqual(close_resp.status_code, 200)
        self.assertEqual(close_resp.json()["status"], "CLOSED")

    def test_cross_user_isolation(self):
        other_proc = Process.objects.create(
            owner=self.other_user,
            title="Secret",
            process_type=Process.ProcessType.LINEAR,
        )
        resp = self.client.get(f"/api/v1/processes/{other_proc.pk}/")
        self.assertEqual(resp.status_code, 404)

    def test_permission_denied_for_modifying_another_users_process_and_steps(
        self,
    ):
        """کاربر نباید بتواند پروسه یا مراحل کاربر دیگر را ویرایش، حذف یا تغییر وضعیت دهد."""
        other_proc = Process.objects.create(
            owner=self.other_user,
            title="Other User Process",
            process_type=Process.ProcessType.LINEAR,
        )
        other_form = Form.objects.create(
            owner=self.other_user,
            title="Other Form",
            status=Form.Status.PUBLISHED,
        )
        other_step = ProcessStep.objects.create(
            process=other_proc,
            form=other_form,
            order=1,
        )

        # تلاش برای ویرایش پروسه کاربر دیگر
        patch_resp = self.client.patch(
            f"/api/v1/processes/{other_proc.pk}/",
            data={"title": "Hacked Title"},
            format="json",
        )
        self.assertEqual(patch_resp.status_code, 404)

        # تلاش برای حذف پروسه کاربر دیگر
        del_resp = self.client.delete(f"/api/v1/processes/{other_proc.pk}/")
        self.assertEqual(del_resp.status_code, 404)

        # تلاش برای انتشار پروسه کاربر دیگر
        pub_resp = self.client.post(f"/api/v1/processes/{other_proc.pk}/publish/")
        self.assertEqual(pub_resp.status_code, 404)

        # تلاش برای بستن پروسه کاربر دیگر
        close_resp = self.client.post(f"/api/v1/processes/{other_proc.pk}/close/")
        self.assertEqual(close_resp.status_code, 404)

        # تلاش برای افزودن استپ به پروسه کاربر دیگر
        add_step_resp = self.client.post(
            f"/api/v1/processes/{other_proc.pk}/steps/",
            data={"form_id": self.form1.pk},
            format="json",
        )
        self.assertEqual(add_step_resp.status_code, 404)

        # تلاش برای حذف استپ پروسه کاربر دیگر
        del_step_resp = self.client.delete(
            f"/api/v1/processes/{other_proc.pk}/steps/{other_step.pk}/"
        )
        self.assertEqual(del_step_resp.status_code, 404)

    def test_cannot_add_unauthorized_or_nonexistent_form_to_step(self):
        """افزودن فرم کاربر دیگر یا فرم ناموجود به استپ باید رد شود."""
        proc = Process.objects.create(
            owner=self.user,
            title="My Process",
            process_type=Process.ProcessType.LINEAR,
        )
        other_form = Form.objects.create(
            owner=self.other_user,
            title="Unauthorized Form",
            status=Form.Status.PUBLISHED,
        )

        # فرم متعلق به کاربر دیگر
        resp_other = self.client.post(
            f"/api/v1/processes/{proc.pk}/steps/",
            data={"form_id": other_form.pk},
            format="json",
        )
        self.assertEqual(resp_other.status_code, 400)
        self.assertEqual(resp_other.json()["error_code"], "PROCESS_VALIDATION_ERROR")
        self.assertIn("form_id", resp_other.json()["field_errors"])

        # فرم با شناسه ناموجود
        resp_404 = self.client.post(
            f"/api/v1/processes/{proc.pk}/steps/",
            data={"form_id": 999999},
            format="json",
        )
        self.assertEqual(resp_404.status_code, 400)
        self.assertIn("form_id", resp_404.json()["field_errors"])

    def test_invalid_step_reorder_inputs(self):
        """بررسی خطاهای مختلف ورودی در Reorder استپ‌ها."""
        proc = Process.objects.create(
            owner=self.user,
            title="Reorder Process",
            process_type=Process.ProcessType.LINEAR,
        )
        s1 = ProcessStep.objects.create(process=proc, form=self.form1, order=1)
        ProcessStep.objects.create(process=proc, form=self.form2, order=2)

        # ۱. ارسال استپ تکراری (Duplicate ID)
        resp_dup = self.client.post(
            f"/api/v1/processes/{proc.pk}/steps/reorder/",
            data={"step_ids": [s1.pk, s1.pk]},
            format="json",
        )
        self.assertEqual(resp_dup.status_code, 400)
        self.assertEqual(resp_dup.json()["error_code"], "PROCESS_VALIDATION_ERROR")

        # ۲. جا انداختن یکی از استپ‌ها (Missing ID)
        resp_miss = self.client.post(
            f"/api/v1/processes/{proc.pk}/steps/reorder/",
            data={"step_ids": [s1.pk]},
            format="json",
        )
        self.assertEqual(resp_miss.status_code, 400)

        # ۳. ارسال شناسه نامعتبر یا متعلق به پروسه دیگر
        resp_foreign = self.client.post(
            f"/api/v1/processes/{proc.pk}/steps/reorder/",
            data={"step_ids": [s1.pk, 999999]},
            format="json",
        )
        self.assertEqual(resp_foreign.status_code, 400)
