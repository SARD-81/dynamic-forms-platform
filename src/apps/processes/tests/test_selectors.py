from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.models import Category
from apps.forms.models import Form
from apps.processes.models import Process, ProcessStep
from apps.processes.selectors import (
    get_available_forms_for_owner,
    get_process_for_owner,
    get_process_step_for_owner,
    get_process_steps_for_owner,
    get_processes_for_owner,
)

User = get_user_model()


class ProcessSelectorsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="password"
        )
        self.other = User.objects.create_user(
            username="other", email="other@test.com", password="password"
        )
        self.category = Category.objects.create(name="HR", owner=self.owner)

        self.form1 = Form.objects.create(
            owner=self.owner, title="Form 1", status=Form.Status.PUBLISHED
        )
        self.form2 = Form.objects.create(
            owner=self.owner, title="Form 2", status=Form.Status.PUBLISHED
        )
        self.other_form = Form.objects.create(
            owner=self.other, title="Other Form", status=Form.Status.PUBLISHED
        )

        self.process = Process.objects.create(
            owner=self.owner,
            category=self.category,
            title="Hiring",
            process_type=Process.ProcessType.LINEAR,
        )
        self.step1 = ProcessStep.objects.create(process=self.process, form=self.form1, order=1)
        self.step2 = ProcessStep.objects.create(process=self.process, form=self.form2, order=2)

    def test_get_processes_for_owner_isolation(self):
        Process.objects.create(
            owner=self.other,
            title="Other Process",
            process_type=Process.ProcessType.FREE,
        )
        processes = list(get_processes_for_owner(owner=self.owner))
        self.assertEqual(len(processes), 1)
        self.assertEqual(processes[0].pk, self.process.pk)

    def test_get_process_for_owner(self):
        proc = get_process_for_owner(owner=self.owner, process_id=self.process.pk)
        self.assertIsNotNone(proc)
        self.assertEqual(proc.pk, self.process.pk)

        # Cross-user query returns None
        proc_other = get_process_for_owner(owner=self.other, process_id=self.process.pk)
        self.assertIsNone(proc_other)

    def test_get_process_steps_ordered(self):
        steps = list(get_process_steps_for_owner(owner=self.owner, process_id=self.process.pk))
        self.assertEqual(len(steps), 2)
        self.assertEqual([s.pk for s in steps], [self.step1.pk, self.step2.pk])
        self.assertEqual([s.order for s in steps], [1, 2])

    def test_get_process_step_for_owner(self):
        step = get_process_step_for_owner(
            owner=self.owner,
            process_id=self.process.pk,
            step_id=self.step1.pk,
        )
        self.assertIsNotNone(step)
        self.assertEqual(step.pk, self.step1.pk)

        # Non-existent or other user step returns None
        step_none = get_process_step_for_owner(
            owner=self.other,
            process_id=self.process.pk,
            step_id=self.step1.pk,
        )
        self.assertIsNone(step_none)

    def test_get_available_forms_for_owner(self):
        available_forms = list(get_available_forms_for_owner(owner=self.owner))
        self.assertEqual(len(available_forms), 2)
        self.assertNotIn(self.other_form, available_forms)
