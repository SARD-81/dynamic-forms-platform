from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from apps.reports.models import ReportSubscription
from apps.reports.serializers import ReportSubscriptionSerializer
from apps.reports.services import create_report_subscription

User = get_user_model()


class ReportSubscriptionSerializerTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staff", email="staff@example.com", password="password123", is_staff=True
        )

    def test_valid_email_subscription_serialization(self):
        sub = create_report_subscription(
            user=self.staff_user,
            frequency=ReportSubscription.Frequency.WEEKLY,
            delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            email="target@example.com",
        )
        serializer = ReportSubscriptionSerializer(instance=sub)
        data = serializer.data

        self.assertEqual(data["id"], sub.pk)
        self.assertEqual(data["frequency"], "WEEKLY")
        self.assertEqual(data["delivery_method"], "EMAIL")
        self.assertEqual(data["email"], "target@example.com")
        self.assertIsNone(data["endpoint_url"])
        self.assertEqual(data["created_by_username"], self.staff_user.username)

    def test_serializer_validation_rejects_xor_violations(self):
        # هر دو مقصد مشخص شده باشد
        invalid_data = {
            "frequency": "WEEKLY",
            "delivery_method": "EMAIL",
            "email": "test@example.com",
            "endpoint_url": "https://api.example.com",
        }
        serializer = ReportSubscriptionSerializer(data=invalid_data)
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

        # هیچ مقصدی مشخص نشده باشد
        empty_data = {
            "frequency": "WEEKLY",
            "delivery_method": "EMAIL",
        }
        empty_serializer = ReportSubscriptionSerializer(data=empty_data)
        with self.assertRaises(ValidationError):
            empty_serializer.is_valid(raise_exception=True)

    def test_serializer_validation_rejects_invalid_url(self):
        invalid_url_data = {
            "frequency": "MONTHLY",
            "delivery_method": "API",
            "endpoint_url": "invalid-url",
        }
        serializer = ReportSubscriptionSerializer(data=invalid_url_data)
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)
