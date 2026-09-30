from django.test import TestCase
from django.urls import reverse


class Gate3AcceptanceContractTests(TestCase):
    def test_openapi_schema_covers_mandatory_gate3_rest_surfaces(self):
        response = self.client.get(reverse("schema"), {"format": "json"})
        self.assertEqual(response.status_code, 200)

        paths = response.json()["paths"]
        expected_paths = {
            "/api/v1/accounts/login/",
            "/api/v1/categories/",
            "/api/v1/forms/",
            "/api/v1/forms/{form_id}/report/",
            "/api/v1/processes/",
            "/api/v1/processes/{process_id}/report/",
            "/api/v1/reports/subscriptions/",
            "/api/v1/public/forms/{public_id}/submissions/",
            "/api/v1/public/processes/{public_id}/runs/",
        }

        missing = expected_paths.difference(paths)
        self.assertFalse(missing, f"Mandatory Gate 3 API paths missing from OpenAPI: {sorted(missing)}")

    def test_api_root_and_swagger_are_available_together(self):
        api_root = self.client.get("/api/v1/")
        swagger = self.client.get(reverse("swagger-ui"))

        self.assertEqual(api_root.status_code, 200)
        self.assertEqual(api_root.json()["version"], "1.0.0")
        self.assertEqual(swagger.status_code, 200)
