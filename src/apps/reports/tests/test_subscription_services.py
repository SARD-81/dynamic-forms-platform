import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.reports.models import ReportSubscription
from apps.reports.selectors import (
    get_due_report_subscriptions,
    get_report_subscription_for_admin,
    get_report_subscriptions_for_admin,
)
from apps.reports.services import (
    activate_report_subscription,
    create_report_subscription,
    deactivate_report_subscription,
    record_subscription_sent,
    update_report_subscription,
)

User = get_user_model()


class ReportSubscriptionServicesTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="super", email="super@example.com", password="password123"
        )
        self.staff_user = User.objects.create_user(
            username="staff", email="staff@example.com", password="password123", is_staff=True
        )
        self.normal_user = User.objects.create_user(
            username="normal", email="normal@example.com", password="password123"
        )

    def test_staff_and_superuser_allowed_to_create_subscription(self):
        sub_staff = create_report_subscription(
            user=self.staff_user,
            frequency=ReportSubscription.Frequency.WEEKLY,
            delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            email="reports@example.com",
        )
        self.assertEqual(sub_staff.created_by, self.staff_user)
        self.assertEqual(sub_staff.email, "reports@example.com")

        sub_super = create_report_subscription(
            user=self.superuser,
            frequency=ReportSubscription.Frequency.MONTHLY,
            delivery_method=ReportSubscription.DeliveryMethod.API,
            endpoint_url="https://api.example.com/webhook",
        )
        self.assertEqual(sub_super.created_by, self.superuser)
        self.assertEqual(sub_super.endpoint_url, "https://api.example.com/webhook")

    def test_normal_and_anonymous_users_denied(self):
        with self.assertRaises(PermissionDenied):
            create_report_subscription(
                user=self.normal_user,
                frequency=ReportSubscription.Frequency.WEEKLY,
                delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
                email="reports@example.com",
            )

        with self.assertRaises(PermissionDenied):
            create_report_subscription(
                user=None,
                frequency=ReportSubscription.Frequency.WEEKLY,
                delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
                email="reports@example.com",
            )

    def test_frequency_validation(self):
        with self.assertRaises(ValidationError) as ctx:
            create_report_subscription(
                user=self.staff_user,
                frequency="HOURLY",
                delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
                email="reports@example.com",
            )
        self.assertIn("frequency", ctx.exception.message_dict)

    def test_email_target_validation(self):
        with self.assertRaises(ValidationError) as ctx:
            create_report_subscription(
                user=self.staff_user,
                frequency=ReportSubscription.Frequency.WEEKLY,
                delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
                email="not-an-email",
            )
        self.assertIn("email", ctx.exception.message_dict)

    def test_api_url_target_validation(self):
        with self.assertRaises(ValidationError) as ctx:
            create_report_subscription(
                user=self.staff_user,
                frequency=ReportSubscription.Frequency.WEEKLY,
                delivery_method=ReportSubscription.DeliveryMethod.API,
                endpoint_url="invalid-url",
            )
        self.assertIn("endpoint_url", ctx.exception.message_dict)

    def test_delivery_target_xor_both_targets_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            create_report_subscription(
                user=self.staff_user,
                frequency=ReportSubscription.Frequency.WEEKLY,
                delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
                email="reports@example.com",
                endpoint_url="https://api.example.com/webhook",
            )
        self.assertIn("delivery_target", ctx.exception.message_dict)

    def test_delivery_target_xor_neither_target_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            create_report_subscription(
                user=self.staff_user,
                frequency=ReportSubscription.Frequency.WEEKLY,
                delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            )
        self.assertIn("delivery_target", ctx.exception.message_dict)

    def test_mismatched_target_and_method_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            create_report_subscription(
                user=self.staff_user,
                frequency=ReportSubscription.Frequency.WEEKLY,
                delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
                endpoint_url="https://api.example.com/webhook",
            )
        self.assertIn("email", ctx.exception.message_dict)
        self.assertIn("endpoint_url", ctx.exception.message_dict)

    def test_update_subscription(self):
        sub = create_report_subscription(
            user=self.staff_user,
            frequency=ReportSubscription.Frequency.WEEKLY,
            delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            email="reports@example.com",
        )

        updated = update_report_subscription(
            subscription_id=sub.pk,
            user=self.staff_user,
            frequency=ReportSubscription.Frequency.MONTHLY,
            delivery_method=ReportSubscription.DeliveryMethod.API,
            email="",
            endpoint_url="https://api.example.com/new-webhook",
        )
        self.assertEqual(updated.frequency, ReportSubscription.Frequency.MONTHLY)
        self.assertEqual(updated.delivery_method, ReportSubscription.DeliveryMethod.API)
        self.assertIsNone(updated.email)
        self.assertEqual(updated.endpoint_url, "https://api.example.com/new-webhook")

    def test_deactivate_and_activate_subscription(self):
        sub = create_report_subscription(
            user=self.staff_user,
            frequency=ReportSubscription.Frequency.WEEKLY,
            delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            email="reports@example.com",
        )
        self.assertTrue(sub.is_active)

        deactivated = deactivate_report_subscription(
            subscription_id=sub.pk,
            user=self.staff_user,
        )
        self.assertFalse(deactivated.is_active)

        activated = activate_report_subscription(
            subscription_id=sub.pk,
            user=self.staff_user,
        )
        self.assertTrue(activated.is_active)

    def test_record_subscription_sent(self):
        sub = create_report_subscription(
            user=self.staff_user,
            frequency=ReportSubscription.Frequency.WEEKLY,
            delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            email="reports@example.com",
        )
        self.assertIsNone(sub.last_sent_at)

        sent_time = timezone.now()
        updated = record_subscription_sent(subscription_id=sub.pk, sent_at=sent_time)
        self.assertEqual(updated.last_sent_at, sent_time)

    def test_selectors_admin_and_inactive_handling(self):
        sub1 = create_report_subscription(
            user=self.staff_user,
            frequency=ReportSubscription.Frequency.WEEKLY,
            delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            email="sub1@example.com",
        )
        sub2 = create_report_subscription(
            user=self.staff_user,
            frequency=ReportSubscription.Frequency.MONTHLY,
            delivery_method=ReportSubscription.DeliveryMethod.API,
            endpoint_url="https://api.example.com/sub2",
            is_active=False,
        )

        # عدم دسترسی کاربر عادی
        with self.assertRaises(PermissionDenied):
            get_report_subscriptions_for_admin(user=self.normal_user)

        with self.assertRaises(PermissionDenied):
            get_report_subscription_for_admin(subscription_id=sub1.pk, user=self.normal_user)

        # دسترسی ادمین و فیلترها
        all_subs = list(get_report_subscriptions_for_admin(user=self.staff_user))
        self.assertEqual(len(all_subs), 2)

        active_subs = list(get_report_subscriptions_for_admin(user=self.staff_user, is_active=True))
        self.assertEqual(active_subs, [sub1])

        single = get_report_subscription_for_admin(subscription_id=sub2.pk, user=self.superuser)
        self.assertEqual(single, sub2)

    def test_due_subscription_selector(self):
        now = timezone.now()
        eight_days_ago = now - datetime.timedelta(days=8)
        two_days_ago = now - datetime.timedelta(days=2)

        # ۱. هرگز ارسال نشده -> Due
        sub_never = create_report_subscription(
            user=self.staff_user,
            frequency=ReportSubscription.Frequency.WEEKLY,
            delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            email="never@example.com",
        )

        # ۲. ۸ روز پیش ارسال شده -> Due
        sub_old = create_report_subscription(
            user=self.staff_user,
            frequency=ReportSubscription.Frequency.WEEKLY,
            delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            email="old@example.com",
        )
        record_subscription_sent(subscription_id=sub_old.pk, sent_at=eight_days_ago)

        # ۳. ۲ روز پیش ارسال شده -> Not Due
        sub_recent = create_report_subscription(
            user=self.staff_user,
            frequency=ReportSubscription.Frequency.WEEKLY,
            delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            email="recent@example.com",
        )
        record_subscription_sent(subscription_id=sub_recent.pk, sent_at=two_days_ago)

        # ۴. موعد گذشته اما غیرفعال -> Not Due
        sub_inactive = create_report_subscription(
            user=self.staff_user,
            frequency=ReportSubscription.Frequency.WEEKLY,
            delivery_method=ReportSubscription.DeliveryMethod.EMAIL,
            email="inactive@example.com",
            is_active=False,
        )

        due = list(
            get_due_report_subscriptions(frequency=ReportSubscription.Frequency.WEEKLY, as_of=now)
        )
        self.assertIn(sub_never, due)
        self.assertIn(sub_old, due)
        self.assertNotIn(sub_recent, due)
        self.assertNotIn(sub_inactive, due)
