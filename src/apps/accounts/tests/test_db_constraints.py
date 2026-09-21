from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import OTPChallenge, User


class AccountDatabaseConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="constraint-user",
            email="constraint@example.com",
            password="test-password",
        )

    def test_user_email_must_be_unique(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username="second-user",
                    email=self.user.email,
                    password="test-password",
                )

    def test_otp_attempt_count_cannot_be_negative(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OTPChallenge.objects.create(
                    user=self.user,
                    purpose=OTPChallenge.Purpose.LOGIN,
                    code_hash="hash",
                    expires_at=timezone.now() + timedelta(minutes=5),
                    attempt_count=-1,
                )
