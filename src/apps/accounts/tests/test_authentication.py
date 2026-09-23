import re
from datetime import timedelta

import pytest
from django.contrib.auth.hashers import check_password
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.exceptions import (
    AccountValidationError,
    AuthenticationFailedError,
    InactiveAccountError,
    OTPAlreadyVerifiedError,
    OTPAttemptsExceededError,
    OTPCooldownError,
    OTPEmailDeliveryError,
    OTPExpiredError,
    OTPInvalidCodeError,
    OTPRateLimitError,
)
from apps.accounts.models import OTPChallenge, User
from apps.accounts.services import (
    login_user,
    register_user,
    resend_registration_otp,
    verify_registration_otp,
)

pytestmark = pytest.mark.django_db(transaction=True)

PASSWORD = "strong-password-123"
OTP_PATTERN = re.compile(r"\b(\d{6})\b")


@pytest.fixture(autouse=True)
def clear_mailbox():
    if hasattr(mail, "outbox"):
        mail.outbox.clear()


def _mail_code():
    assert mail.outbox
    match = OTP_PATTERN.search(mail.outbox[-1].body)
    assert match is not None
    return match.group(1)


def _register_pending(
    *,
    username="pending-user",
    email="pending@example.com",
    password=PASSWORD,
):
    user = register_user(
        username=username,
        email=email,
        password=password,
    )
    return user, _mail_code()


def _wrong_code(code):
    return "999999" if code != "999999" else "888888"


def test_registration_creates_inactive_user_and_never_persists_raw_otp(monkeypatch):
    monkeypatch.setattr(
        "apps.accounts.services.secrets.randbelow",
        lambda upper_bound: 42,
    )

    user, code = _register_pending()

    assert code == "000042"
    assert user.is_active is False

    challenge = OTPChallenge.objects.get(user=user)
    assert challenge.code_hash != code
    assert code not in challenge.code_hash
    assert check_password(code, challenge.code_hash)
    assert challenge.attempt_count == 0
    assert challenge.verified_at is None


def test_registration_rejects_duplicate_email_and_weak_password():
    _register_pending(email="duplicate@example.com")

    with pytest.raises(AccountValidationError) as duplicate:
        register_user(
            username="another-user",
            email="DUPLICATE@example.com",
            password=PASSWORD,
        )

    assert "email" in duplicate.value.errors

    with pytest.raises(AccountValidationError) as weak:
        register_user(
            username="weak-user",
            email="weak@example.com",
            password="short",
        )

    assert "password" in weak.value.errors


def test_expired_otp_cannot_activate_account():
    user, code = _register_pending()
    OTPChallenge.objects.filter(user=user).update(expires_at=timezone.now() - timedelta(seconds=1))

    with pytest.raises(OTPExpiredError):
        verify_registration_otp(email=user.email, code=code)

    user.refresh_from_db()
    assert user.is_active is False


def test_wrong_otp_increments_attempt_count():
    user, code = _register_pending()
    wrong = _wrong_code(code)

    with pytest.raises(OTPInvalidCodeError):
        verify_registration_otp(email=user.email, code=wrong)

    challenge = OTPChallenge.objects.get(user=user)
    assert challenge.attempt_count == 1


def test_otp_attempt_exhaustion_blocks_even_the_correct_code():
    user, code = _register_pending()
    wrong = _wrong_code(code)

    for attempt in range(1, 6):
        error = OTPAttemptsExceededError if attempt == 5 else OTPInvalidCodeError
        with pytest.raises(error):
            verify_registration_otp(email=user.email, code=wrong)

    challenge = OTPChallenge.objects.get(user=user)
    assert challenge.attempt_count == 5

    with pytest.raises(OTPAttemptsExceededError):
        verify_registration_otp(email=user.email, code=code)


def test_verified_otp_is_one_time_use():
    user, code = _register_pending()

    verified = verify_registration_otp(email=user.email, code=code)
    assert verified.is_active is True

    challenge = OTPChallenge.objects.get(user=user)
    assert challenge.verified_at is not None

    with pytest.raises(OTPAlreadyVerifiedError):
        verify_registration_otp(email=user.email, code=code)


@override_settings(ACCOUNT_OTP_RESEND_COOLDOWN_SECONDS=0)
def test_resend_expires_previous_code_and_creates_new_challenge():
    user, old_code = _register_pending()
    previous = OTPChallenge.objects.get(user=user)

    resend_registration_otp(email=user.email)
    new_code = _mail_code()

    previous.refresh_from_db()
    latest = OTPChallenge.objects.filter(user=user).order_by("-created_at").first()

    assert latest.pk != previous.pk
    assert previous.expires_at <= timezone.now()
    assert previous.verified_at is None
    assert check_password(new_code, latest.code_hash)
    assert not check_password(old_code, latest.code_hash)


def test_resend_cooldown_blocks_immediate_repeat():
    user, _ = _register_pending()

    with pytest.raises(OTPCooldownError) as error:
        resend_registration_otp(email=user.email)

    assert error.value.retry_after > 0


@override_settings(ACCOUNT_OTP_RESEND_COOLDOWN_SECONDS=0)
def test_resend_rate_limit_is_five_sends_per_window():
    user, _ = _register_pending()

    for _ in range(4):
        resend_registration_otp(email=user.email)

    assert OTPChallenge.objects.filter(user=user).count() == 5

    with pytest.raises(OTPRateLimitError) as error:
        resend_registration_otp(email=user.email)

    assert error.value.retry_after > 0


def test_email_delivery_failure_preserves_coherent_pending_state(monkeypatch):
    def fail_send(*args, **kwargs):
        raise RuntimeError("mail transport failed")

    monkeypatch.setattr("apps.accounts.services.send_mail", fail_send)

    with pytest.raises(OTPEmailDeliveryError):
        register_user(
            username="mail-failure",
            email="mail-failure@example.com",
            password=PASSWORD,
        )

    user = User.objects.get(username="mail-failure")
    challenge = OTPChallenge.objects.get(user=user)

    assert user.is_active is False
    assert challenge.verified_at is None
    assert challenge.expires_at > timezone.now()


def test_html_registration_verification_login_and_logout_flow(client):
    register_response = client.post(
        reverse("accounts:register"),
        {
            "username": "html-user",
            "email": "html@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
        },
    )

    assert register_response.status_code == 302
    assert register_response.url == reverse("accounts:verify")
    code = _mail_code()

    verify_response = client.post(
        reverse("accounts:verify"),
        {
            "verify-email": "html@example.com",
            "verify-code": code,
        },
    )

    assert verify_response.status_code == 302
    assert verify_response.url == reverse("accounts:login")
    assert User.objects.get(username="html-user").is_active is True

    login_response = client.post(
        reverse("accounts:login"),
        {
            "username": "html-user",
            "password": PASSWORD,
            "next": reverse("accounts:me"),
        },
    )

    assert login_response.status_code == 302
    assert login_response.url == reverse("accounts:me")
    assert client.get(reverse("accounts:me")).status_code == 200

    logout_response = client.post(reverse("accounts:logout"))
    assert logout_response.status_code == 302
    assert logout_response.url == reverse("core:home")
    assert client.get(reverse("accounts:me")).status_code == 302


def test_html_login_rejects_inactive_user_and_wrong_password(client):
    User.objects.create_user(
        username="inactive-user",
        email="inactive@example.com",
        password=PASSWORD,
        is_active=False,
    )
    active = User.objects.create_user(
        username="active-user",
        email="active@example.com",
        password=PASSWORD,
    )

    inactive_response = client.post(
        reverse("accounts:login"),
        {
            "username": "inactive-user",
            "password": PASSWORD,
        },
    )
    assert inactive_response.status_code == 200
    assert "Verify your email before signing in." in inactive_response.content.decode()

    wrong_response = client.post(
        reverse("accounts:login"),
        {
            "username": active.username,
            "password": "wrong-password",
        },
    )
    assert wrong_response.status_code == 200
    assert "The username or password is incorrect." in wrong_response.content.decode()


def test_html_current_user_requires_authentication(client):
    response = client.get(reverse("accounts:me"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_api_registration_verification_login_current_user_and_logout_flow():
    api_client = APIClient()

    register_response = api_client.post(
        reverse("accounts_api:register"),
        {
            "username": "api-user",
            "email": "api@example.com",
            "password": PASSWORD,
        },
        format="json",
    )
    assert register_response.status_code == 201
    assert register_response.data["user"]["email"] == "api@example.com"
    code = _mail_code()

    verify_response = api_client.post(
        reverse("accounts_api:verify"),
        {
            "email": "api@example.com",
            "code": code,
        },
        format="json",
    )
    assert verify_response.status_code == 200

    login_response = api_client.post(
        reverse("accounts_api:login"),
        {
            "username": "api-user",
            "password": PASSWORD,
        },
        format="json",
    )
    assert login_response.status_code == 200

    me_response = api_client.get(reverse("accounts_api:me"))
    assert me_response.status_code == 200
    assert me_response.data["username"] == "api-user"

    logout_response = api_client.post(reverse("accounts_api:logout"), format="json")
    assert logout_response.status_code == 204
    assert api_client.get(reverse("accounts_api:me")).status_code == 403


def test_api_current_user_and_logout_require_session_authentication():
    api_client = APIClient()

    assert api_client.get(reverse("accounts_api:me")).status_code == 403
    assert api_client.post(reverse("accounts_api:logout"), format="json").status_code == 403


def test_api_login_requires_csrf_when_checks_are_enforced():
    User.objects.create_user(
        username="csrf-user",
        email="csrf@example.com",
        password=PASSWORD,
    )
    api_client = APIClient(enforce_csrf_checks=True)

    denied = api_client.post(
        reverse("accounts_api:login"),
        {
            "username": "csrf-user",
            "password": PASSWORD,
        },
        format="json",
    )
    assert denied.status_code == 403

    csrf_response = api_client.get(reverse("accounts_api:csrf"))
    assert csrf_response.status_code == 200
    token = csrf_response.data["csrf_token"]

    accepted = api_client.post(
        reverse("accounts_api:login"),
        {
            "username": "csrf-user",
            "password": PASSWORD,
        },
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert accepted.status_code == 200


def test_login_service_rejects_inactive_user_after_validating_password(rf):
    User.objects.create_user(
        username="service-inactive",
        email="service-inactive@example.com",
        password=PASSWORD,
        is_active=False,
    )

    request = rf.post("/accounts/login/")

    with pytest.raises(InactiveAccountError):
        login_user(
            request,
            username="service-inactive",
            password=PASSWORD,
        )


def test_login_service_does_not_disclose_inactive_status_for_wrong_password(rf):
    User.objects.create_user(
        username="private-inactive",
        email="private-inactive@example.com",
        password=PASSWORD,
        is_active=False,
    )

    request = rf.post("/accounts/login/")

    with pytest.raises(AuthenticationFailedError):
        login_user(
            request,
            username="private-inactive",
            password="wrong-password",
        )
