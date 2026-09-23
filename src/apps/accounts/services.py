import math
import secrets
from datetime import timedelta
from functools import partial

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from .exceptions import (
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
    OTPUnavailableError,
)
from .models import OTPChallenge, User
from .selectors import get_user_by_username


def normalize_email(email):
    return User.objects.normalize_email(email.strip()).lower()


def _validation_error_dict(exc, field="__all__"):
    if hasattr(exc, "message_dict"):
        return {key: list(value) for key, value in exc.message_dict.items()}
    return {field: list(exc.messages)}


def _generate_otp():
    upper_bound = 10**settings.ACCOUNT_OTP_LENGTH
    return f"{secrets.randbelow(upper_bound):0{settings.ACCOUNT_OTP_LENGTH}d}"


def _send_registration_otp_email(email, code):
    lifetime_minutes = settings.ACCOUNT_OTP_LIFETIME_SECONDS // 60
    try:
        sent = send_mail(
            subject="Your Dynamic Forms verification code",
            message=(
                f"Your verification code is {code}. It expires in {lifetime_minutes} minutes."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as exc:
        raise OTPEmailDeliveryError from exc

    if sent != 1:
        raise OTPEmailDeliveryError


def _create_registration_challenge(user, now):
    code = _generate_otp()
    challenge = OTPChallenge.objects.create(
        user=user,
        purpose=OTPChallenge.Purpose.REGISTER,
        code_hash=make_password(code),
        expires_at=now + timedelta(seconds=settings.ACCOUNT_OTP_LIFETIME_SECONDS),
    )
    transaction.on_commit(partial(_send_registration_otp_email, user.email, code))
    return challenge


def register_user(*, username, email, password):
    username = username.strip()
    email = normalize_email(email)

    try:
        with transaction.atomic():
            if User.objects.filter(email__iexact=email).exists():
                raise AccountValidationError({"email": ["A user with this email already exists."]})

            user = User(
                username=username,
                email=email,
                is_active=False,
            )

            try:
                user.full_clean(exclude=["password"])
                validate_password(password, user=user)
            except DjangoValidationError as exc:
                field = "password" if not hasattr(exc, "message_dict") else "__all__"
                raise AccountValidationError(_validation_error_dict(exc, field)) from exc

            user.set_password(password)
            user.save()

            _create_registration_challenge(user, timezone.now())
    except IntegrityError as exc:
        errors = {}
        if User.objects.filter(email__iexact=email).exists():
            errors["email"] = ["A user with this email already exists."]
        if User.objects.filter(username=username).exists():
            errors["username"] = ["A user with this username already exists."]
        raise AccountValidationError(
            errors or {"__all__": ["The account could not be created."]}
        ) from exc

    return user


def resend_registration_otp(*, email):
    email = normalize_email(email)
    now = timezone.now()

    with transaction.atomic():
        user = User.objects.select_for_update().filter(email__iexact=email).first()
        if user is None or user.is_active:
            raise OTPUnavailableError

        challenges = OTPChallenge.objects.filter(
            user=user,
            purpose=OTPChallenge.Purpose.REGISTER,
        )
        latest = challenges.order_by("-created_at").first()

        if latest is not None:
            cooldown_end = latest.created_at + timedelta(
                seconds=settings.ACCOUNT_OTP_RESEND_COOLDOWN_SECONDS
            )
            if cooldown_end > now:
                retry_after = math.ceil((cooldown_end - now).total_seconds())
                raise OTPCooldownError(retry_after)

        window_start = now - timedelta(seconds=settings.ACCOUNT_OTP_RATE_LIMIT_WINDOW_SECONDS)
        recent = challenges.filter(created_at__gte=window_start)
        if recent.count() >= settings.ACCOUNT_OTP_RATE_LIMIT_COUNT:
            oldest = recent.order_by("created_at").first()
            retry_after = math.ceil(
                (
                    oldest.created_at
                    + timedelta(seconds=settings.ACCOUNT_OTP_RATE_LIMIT_WINDOW_SECONDS)
                    - now
                ).total_seconds()
            )
            raise OTPRateLimitError(retry_after)

        challenges.filter(
            verified_at__isnull=True,
            expires_at__gt=now,
        ).update(expires_at=now)

        challenge = _create_registration_challenge(user, now)

    return challenge


def verify_registration_otp(*, email, code):
    email = normalize_email(email)
    now = timezone.now()
    verification_error = None
    verified_user = None

    with transaction.atomic():
        user = User.objects.select_for_update().filter(email__iexact=email).first()
        if user is None:
            raise OTPUnavailableError
        if user.is_active:
            raise OTPAlreadyVerifiedError

        challenge = (
            OTPChallenge.objects.select_for_update()
            .filter(
                user=user,
                purpose=OTPChallenge.Purpose.REGISTER,
                verified_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )
        if challenge is None:
            raise OTPUnavailableError
        if challenge.expires_at <= now:
            raise OTPExpiredError
        if challenge.attempt_count >= settings.ACCOUNT_OTP_MAX_ATTEMPTS:
            raise OTPAttemptsExceededError

        if not check_password(code, challenge.code_hash):
            challenge.attempt_count += 1
            challenge.save(update_fields=["attempt_count"])
            if challenge.attempt_count >= settings.ACCOUNT_OTP_MAX_ATTEMPTS:
                verification_error = OTPAttemptsExceededError()
            else:
                verification_error = OTPInvalidCodeError()
        else:
            challenge.verified_at = now
            challenge.save(update_fields=["verified_at"])
            user.is_active = True
            user.save(update_fields=["is_active"])
            verified_user = user

    if verification_error is not None:
        raise verification_error

    return verified_user


def login_user(request, *, username, password):
    username = username.strip()
    candidate = get_user_by_username(username)
    if candidate is not None and not candidate.is_active:
        raise InactiveAccountError

    user = authenticate(request=request, username=username, password=password)
    if user is None:
        raise AuthenticationFailedError

    django_login(request, user)
    return user


def logout_user(request):
    django_logout(request)
