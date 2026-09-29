import pytest
from django.contrib.auth.hashers import check_password
from django.urls import reverse

from apps.accounts.models import User
from apps.forms.models import Form
from apps.processes.models import Process, ProcessStep
from apps.processes.services import create_process_step


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="process-view-other",
        email="process-view-other@example.com",
        password="test-password",
    )


@pytest.fixture
def published_form(user):
    return Form.objects.create(
        owner=user,
        title="Published step form",
        status=Form.Status.PUBLISHED,
    )


@pytest.mark.django_db
def test_process_list_requires_login(client):
    response = client.get(reverse("processes:list"))

    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


@pytest.mark.django_db
def test_process_list_is_owner_scoped(client, user, other_user):
    Process.objects.create(
        owner=user,
        title="Visible process",
        process_type=Process.ProcessType.LINEAR,
    )
    Process.objects.create(
        owner=other_user,
        title="Hidden process",
        process_type=Process.ProcessType.FREE,
    )
    client.force_login(user)

    response = client.get(reverse("processes:list"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Visible process" in content
    assert "Hidden process" not in content


@pytest.mark.django_db
def test_create_and_edit_draft_process_html(client, user):
    client.force_login(user)

    create_response = client.post(
        reverse("processes:create"),
        {
            "title": "Onboarding",
            "description": "First description",
            "category": "",
            "process_type": Process.ProcessType.LINEAR,
            "visibility": Process.Visibility.PUBLIC,
            "access_password": "",
        },
    )

    process = Process.objects.get(owner=user)
    assert create_response.status_code == 302
    assert process.status == Process.Status.DRAFT
    assert process.process_type == Process.ProcessType.LINEAR

    update_response = client.post(
        reverse("processes:update", args=[process.id]),
        {
            "title": "Onboarding updated",
            "description": "Updated description",
            "category": "",
            "process_type": Process.ProcessType.FREE,
            "visibility": Process.Visibility.PUBLIC,
            "access_password": "",
        },
    )

    process.refresh_from_db()
    assert update_response.status_code == 302
    assert process.title == "Onboarding updated"
    assert process.process_type == Process.ProcessType.FREE


@pytest.mark.django_db
def test_private_process_html_hashes_password(client, user):
    client.force_login(user)

    response = client.post(
        reverse("processes:create"),
        {
            "title": "Private flow",
            "description": "",
            "category": "",
            "process_type": Process.ProcessType.LINEAR,
            "visibility": Process.Visibility.PRIVATE,
            "access_password": "process-secret",
        },
    )

    process = Process.objects.get(owner=user)
    assert response.status_code == 302
    assert process.access_password_hash != "process-secret"
    assert check_password("process-secret", process.access_password_hash)


@pytest.mark.django_db
def test_private_process_edit_blank_password_keeps_existing_hash(client, user):
    client.force_login(user)
    create_response = client.post(
        reverse("processes:create"),
        {
            "title": "Private flow",
            "description": "",
            "category": "",
            "process_type": Process.ProcessType.LINEAR,
            "visibility": Process.Visibility.PRIVATE,
            "access_password": "process-secret",
        },
    )
    assert create_response.status_code == 302
    process = Process.objects.get(owner=user)
    original_hash = process.access_password_hash

    update_response = client.post(
        reverse("processes:update", args=[process.id]),
        {
            "title": "Private flow renamed",
            "description": "",
            "category": "",
            "process_type": Process.ProcessType.LINEAR,
            "visibility": Process.Visibility.PRIVATE,
            "access_password": "",
        },
    )

    process.refresh_from_db()
    assert update_response.status_code == 302
    assert process.title == "Private flow renamed"
    assert process.access_password_hash == original_hash
    assert check_password("process-secret", process.access_password_hash)


@pytest.mark.django_db
def test_only_draft_process_can_be_deleted_from_html(client, user, published_form):
    draft = Process.objects.create(
        owner=user,
        title="Delete me",
        process_type=Process.ProcessType.LINEAR,
    )
    client.force_login(user)

    response = client.post(reverse("processes:delete", args=[draft.id]))
    assert response.status_code == 302
    assert not Process.objects.filter(pk=draft.pk).exists()

    published = Process.objects.create(
        owner=user,
        title="Keep me",
        process_type=Process.ProcessType.LINEAR,
        status=Process.Status.PUBLISHED,
    )
    ProcessStep.objects.create(process=published, form=published_form, order=1)

    blocked = client.post(reverse("processes:delete", args=[published.id]))
    assert blocked.status_code == 302
    assert Process.objects.filter(pk=published.pk).exists()


@pytest.mark.django_db
def test_step_form_choices_are_owner_scoped_and_exclude_used_forms(
    client,
    user,
    other_user,
    published_form,
):
    used_form = published_form
    available_form = Form.objects.create(
        owner=user,
        title="Available form",
        status=Form.Status.PUBLISHED,
    )
    foreign_form = Form.objects.create(
        owner=other_user,
        title="Foreign form",
        status=Form.Status.PUBLISHED,
    )
    process = Process.objects.create(
        owner=user,
        title="Choices",
        process_type=Process.ProcessType.LINEAR,
    )
    ProcessStep.objects.create(process=process, form=used_form, order=1)
    client.force_login(user)

    response = client.get(reverse("processes:step_create", args=[process.id]))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Available form" in content
    assert "Published step form" not in content
    assert "Foreign form" not in content
    assert available_form.pk != foreign_form.pk


@pytest.mark.django_db
def test_cross_user_process_detail_returns_404(client, user, other_user):
    process = Process.objects.create(
        owner=other_user,
        title="Hidden",
        process_type=Process.ProcessType.LINEAR,
    )
    client.force_login(user)

    response = client.get(reverse("processes:detail", args=[process.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_process_builder_add_move_and_delete_steps(client, user, published_form):
    second_form = Form.objects.create(
        owner=user,
        title="Second published form",
        status=Form.Status.PUBLISHED,
    )
    process = Process.objects.create(
        owner=user,
        title="Builder",
        process_type=Process.ProcessType.LINEAR,
    )
    client.force_login(user)

    first_add = client.post(
        reverse("processes:step_create", args=[process.id]),
        {"form": published_form.id},
    )
    second_add = client.post(
        reverse("processes:step_create", args=[process.id]),
        {"form": second_form.id},
    )

    assert first_add.status_code == 302
    assert second_add.status_code == 302

    steps = list(ProcessStep.objects.filter(process=process).order_by("order"))
    assert [step.form_id for step in steps] == [published_form.id, second_form.id]

    move_response = client.post(
        reverse(
            "processes:step_move",
            args=[process.id, steps[1].id, "up"],
        )
    )
    assert move_response.status_code == 302

    reordered = list(ProcessStep.objects.filter(process=process).order_by("order"))
    assert [step.form_id for step in reordered] == [second_form.id, published_form.id]

    delete_response = client.post(
        reverse(
            "processes:step_delete",
            args=[process.id, reordered[0].id],
        )
    )
    assert delete_response.status_code == 302

    remaining = ProcessStep.objects.get(process=process)
    assert remaining.order == 1
    assert remaining.form_id == published_form.id


@pytest.mark.django_db
def test_publish_error_and_publish_close_html_flow(client, user, published_form):
    process = Process.objects.create(
        owner=user,
        title="Lifecycle",
        process_type=Process.ProcessType.LINEAR,
    )
    client.force_login(user)

    blocked = client.post(
        reverse("processes:publish", args=[process.id]),
        follow=True,
    )
    process.refresh_from_db()

    assert blocked.status_code == 200
    assert process.status == Process.Status.DRAFT
    assert "Add at least one step before publishing." in blocked.content.decode()

    create_process_step(
        process=process,
        owner=user,
        form_id=published_form.id,
    )
    published_response = client.post(reverse("processes:publish", args=[process.id]))
    process.refresh_from_db()

    assert published_response.status_code == 302
    assert process.status == Process.Status.PUBLISHED

    builder = client.get(reverse("processes:builder", args=[process.id]))
    content = builder.content.decode()
    assert builder.status_code == 200
    assert "execution definition is immutable" in content
    assert "Add step" not in content

    blocked_update = client.post(
        reverse("processes:update", args=[process.id]),
        {
            "title": "Changed",
            "description": "",
            "category": "",
            "process_type": Process.ProcessType.FREE,
            "visibility": Process.Visibility.PUBLIC,
            "access_password": "",
        },
    )
    process.refresh_from_db()
    assert blocked_update.status_code == 302
    assert process.title == "Lifecycle"

    closed_response = client.post(reverse("processes:close", args=[process.id]))
    process.refresh_from_db()

    assert closed_response.status_code == 302
    assert process.status == Process.Status.CLOSED


@pytest.mark.django_db
def test_dashboard_and_navigation_expose_process_management(client, user):
    client.force_login(user)

    response = client.get(reverse("core:dashboard"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Manage processes" in content
    assert reverse("processes:list") in content
    assert ">Processes<" in content
