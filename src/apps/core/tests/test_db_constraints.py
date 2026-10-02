from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import User
from apps.core.models import Category


class CoreDatabaseConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="category-owner",
            email="category-owner@example.com",
            password="test-password",
        )

    def test_category_name_is_unique_per_owner(self):
        Category.objects.create(owner=self.user, name="Shared")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(owner=self.user, name="Shared")
