import pytest


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        username="fixture-user",
        email="fixture-user@example.com",
        password="test-password",
    )


@pytest.fixture
def published_form(db, user):
    from apps.forms.models import Form

    return Form.objects.create(
        owner=user,
        title="Published fixture form",
        visibility=Form.Visibility.PUBLIC,
        status=Form.Status.PUBLISHED,
    )


@pytest.fixture
def linear_process(db, user, published_form):
    from apps.processes.models import Process, ProcessStep

    process = Process.objects.create(
        owner=user,
        title="Linear fixture process",
        process_type=Process.ProcessType.LINEAR,
        visibility=Process.Visibility.PUBLIC,
        status=Process.Status.PUBLISHED,
    )
    ProcessStep.objects.create(
        process=process,
        form=published_form,
        order=1,
    )
    return process
