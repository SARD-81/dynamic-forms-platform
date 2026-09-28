from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.forms.models import Form
from apps.processes.models import Process

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
