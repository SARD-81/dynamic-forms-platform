from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core.models import Category
from apps.forms.models import Form
from apps.processes.models import Process, ProcessStep
from apps.processes.services import (
    close_process,
    create_process,
    create_process_step,
    delete_process_step,
    publish_process,
    reorder_process_steps,
    update_draft_process,
)

User = get_user_model()


class ProcessServicesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner", email="owner@example.com", password="password123"
        )
        self.other_user = User.objects.create_user(
            username="other", email="other@example.com", password="password123"
        )
        self.category = Category.objects.create(name="Onboarding", owner=self.user)
        self.other_category = Category.objects.create(name="Other", owner=self.other_user)

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
        self.draft_form = Form.objects.create(
            owner=self.user,
            title="Draft Form",
            status=Form.Status.DRAFT,
        )

    def test_create_process_draft_public_and_private(self):
        # Public process
        proc = create_process(
            owner=self.user,
            title="HR Process",
            process_type=Process.ProcessType.LINEAR,
            visibility=Process.Visibility.PUBLIC,
        )
        self.assertEqual(proc.status, Process.Status.DRAFT)
        self.assertIsNone(proc.access_password_hash)

        # Private process
        proc_priv = create_process(
            owner=self.user,
            title="Confidential",
            process_type=Process.ProcessType.FREE,
            visibility=Process.Visibility.PRIVATE,
            access_password="SecretPassword1",
        )
        self.assertTrue(check_password("SecretPassword1", proc_priv.access_password_hash))

    def test_create_process_private_without_password_fails(self):
        with self.assertRaises(ValidationError):
            create_process(
                owner=self.user,
                title="Invalid Private",
                process_type=Process.ProcessType.LINEAR,
                visibility=Process.Visibility.PRIVATE,
                access_password=None,
            )

    def test_category_ownership_validation(self):
        with self.assertRaises(ValidationError):
            create_process(
                owner=self.user,
                title="Wrong Category",
                process_type=Process.ProcessType.LINEAR,
                category_id=self.other_category.pk,
            )

    def test_step_management_contiguous_and_duplicate_rejection(self):
        proc = create_process(
            owner=self.user,
            title="Flow",
            process_type=Process.ProcessType.LINEAR,
        )
        s1 = create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        s2 = create_process_step(process=proc, owner=self.user, form_id=self.form2.pk)

        self.assertEqual(s1.order, 1)
        self.assertEqual(s2.order, 2)

        # Re-adding same form should fail
        with self.assertRaises(ValidationError):
            create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)

        # Reordering steps
        reordered = reorder_process_steps(process=proc, owner=self.user, step_ids=[s2.pk, s1.pk])
        self.assertEqual([s.pk for s in reordered], [s2.pk, s1.pk])
        self.assertEqual([s.order for s in reordered], [1, 2])

        # Deleting step restores contiguous order
        delete_process_step(process=proc, owner=self.user, step_id=s2.pk)
        remaining = ProcessStep.objects.filter(process=proc)
        self.assertEqual(remaining.count(), 1)
        self.assertEqual(remaining.first().order, 1)

    def test_publish_readiness_validations(self):
        proc = create_process(
            owner=self.user,
            title="Flow",
            process_type=Process.ProcessType.LINEAR,
        )

        # Cannot publish without steps
        with self.assertRaises(ValidationError):
            publish_process(process=proc, owner=self.user)

        # Cannot publish with draft form
        step = create_process_step(process=proc, owner=self.user, form_id=self.draft_form.pk)
        with self.assertRaises(ValidationError):
            publish_process(process=proc, owner=self.user)

        # Replace with published form and publish successfully
        step.delete()
        create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        published = publish_process(process=proc, owner=self.user)
        self.assertEqual(published.status, Process.Status.PUBLISHED)

        # Once published, steps cannot be modified
        with self.assertRaises(ValidationError):
            create_process_step(process=published, owner=self.user, form_id=self.form2.pk)

        with self.assertRaises(ValidationError):
            update_draft_process(process=published, owner=self.user, title="New Title")

        # Can close from published
        closed = close_process(process=published, owner=self.user)
        self.assertEqual(closed.status, Process.Status.CLOSED)

        # Cannot close draft directly
        draft_proc = create_process(
            owner=self.user,
            title="Draft Only",
            process_type=Process.ProcessType.LINEAR,
        )
        with self.assertRaises(ValidationError):
            close_process(process=draft_proc, owner=self.user)

    def test_publish_process_locks_step_forms_with_select_for_update(self):
        """انتشار پروسه باید فرم‌های متصل را برای جلوگیری از تغییر هم‌زمان قفل کند."""
        proc = create_process(
            owner=self.user,
            title="Locking Flow",
            process_type=Process.ProcessType.LINEAR,
        )
        create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)
        create_process_step(process=proc, owner=self.user, form_id=self.form2.pk)

        with patch.object(
            Form.objects, "select_for_update", wraps=Form.objects.select_for_update
        ) as mock_sfu:
            published = publish_process(process=proc, owner=self.user)
            self.assertEqual(published.status, Process.Status.PUBLISHED)
            mock_sfu.assert_called()

    def test_publish_process_fails_if_step_form_is_closed(self):
        """اگر فرمی هم‌زمان یا قبلاً بسته شده باشد، انتشار باید با خطا متوقف شود."""
        proc = create_process(
            owner=self.user,
            title="Closed Form Flow",
            process_type=Process.ProcessType.LINEAR,
        )
        create_process_step(process=proc, owner=self.user, form_id=self.form1.pk)

        # تغییر وضعیت فرم به CLOSED
        self.form1.status = Form.Status.CLOSED
        self.form1.save(update_fields=["status"])

        with self.assertRaises(ValidationError) as ctx:
            publish_process(process=proc, owner=self.user)
        self.assertIn("forms", ctx.exception.message_dict)
