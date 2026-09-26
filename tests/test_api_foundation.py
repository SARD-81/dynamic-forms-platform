from django.test import TestCase
from django.urls import resolve, reverse
from django.urls.exceptions import Resolver404


class APIFoundationTests(TestCase):
    def test_schema_endpoint_returns_200_and_contains_accounts(self):
        """Schema endpoint 200 بده و حداقل یکی از مسیرهای accounts در خروجی باشد"""
        response = self.client.get(reverse("schema"))
        self.assertEqual(response.status_code, 200)
        # بررسی وجود مسیر واقعی در محتوای OpenAPI تولیدشده
        self.assertIn(b"/api/v1/accounts/", response.content)

    def test_swagger_docs_returns_200(self):
        """Swagger docs بالا بیاد"""
        response = self.client.get(reverse("swagger-ui"))
        self.assertEqual(response.status_code, 200)

    def test_api_v1_base_routing_resolves(self):
        """تست resolve شدن مسیرهای زیرمجموعه /api/v1/ در روتر مرکزی"""
        try:
            match = resolve("/api/v1/accounts/login/")
            self.assertTrue(match.func)
        except Resolver404:
            self.fail("The base API router /api/v1/ failed to resolve valid sub-paths.")

    def test_admin_and_html_auth_routes_do_not_break(self):
        """Admin و HTML Auth routes نشکنن"""
        admin_response = self.client.get("/admin/login/")
        self.assertEqual(admin_response.status_code, 200)

        html_auth_response = self.client.get("/accounts/login/")
        self.assertEqual(html_auth_response.status_code, 200)

    def test_accounts_api_integrated_and_resolves(self):
        """Accounts API بعد از Integration همچنان کار کنه"""
        response = self.client.post("/api/v1/accounts/login/")
        self.assertEqual(response.status_code, 400)

    def test_protected_endpoint_without_auth(self):
        """Protected endpoint بدون Auth رفتار مشخص داشته باشه"""
        response = self.client.get("/api/v1/accounts/me/")
        self.assertEqual(response.status_code, 403)

    def test_404_handler_is_active(self):
        """403/404 handlerها سر جاشون باشن"""
        response = self.client.get("/api/v1/this-route-does-not-exist/")
        self.assertEqual(response.status_code, 404)
