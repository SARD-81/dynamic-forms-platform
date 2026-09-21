from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import User
from apps.reports.models import ReportSubscription


class ReportDatabaseConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="report-admin",
            email="report-admin@example.com",
            password="test-password",
        )

    def test_email_delivery_requires_only_email(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ReportSubscription.objects.create(
                    created_by=self.user,
                    frequency=ReportSubscription.Frequency.WEEKLY,
                    delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
                    email=None,
                    endpoint_url=None,
                )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ReportSubscription.objects.create(
                    created_by=self.user,
                    frequency=ReportSubscription.Frequency.WEEKLY,
                    delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
                    email="reports@example.com",
                    endpoint_url="https://example.com/report",
                )

    def test_api_delivery_requires_only_endpoint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ReportSubscription.objects.create(
                    created_by=self.user,
                    frequency=ReportSubscription.Frequency.MONTHLY,
                    delivery_method=ReportSubscription.DeliveryMethod.API,
                    email="reports@example.com",
                    endpoint_url="https://example.com/report",
                )
