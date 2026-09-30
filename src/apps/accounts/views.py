from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .exceptions import (
    AccountServiceError,
    AccountValidationError,
    OTPAlreadyVerifiedError,
    OTPEmailDeliveryError,
    OTPThrottleError,
)
from .forms import LoginForm, OTPResendForm, OTPVerificationForm, RegistrationForm
from .services import (
    login_user,
    logout_user,
    register_user,
    resend_registration_otp,
    verify_registration_otp,
)

PENDING_EMAIL_SESSION_KEY = "pending_verification_email"


def _add_validation_errors(form, exc):
    for field, errors in exc.errors.items():
        target = {
            "password": "password1",
            "__all__": None,
        }.get(field, field)
        if target not in form.fields:
            target = None
        for error in errors:
            form.add_error(target, error)


def _verification_context(*, verification_form=None, resend_form=None):
    return {
        "verification_form": verification_form or OTPVerificationForm(prefix="verify"),
        "resend_form": resend_form or OTPResendForm(prefix="resend"),
    }


def _safe_next_url(request, candidate):
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return reverse("core:dashboard")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            try:
                register_user(
                    username=form.cleaned_data["username"],
                    email=email,
                    password=form.cleaned_data["password1"],
                )
            except AccountValidationError as exc:
                _add_validation_errors(form, exc)
            except OTPEmailDeliveryError:
                request.session[PENDING_EMAIL_SESSION_KEY] = email
                messages.warning(
                    request,
                    (
                        "Your account was created, but the email could not be delivered. "
                        "You can request another code shortly."
                    ),
                )
                return redirect("accounts:verify")
            else:
                request.session[PENDING_EMAIL_SESSION_KEY] = email
                messages.success(
                    request,
                    "Account created. Check your email for the verification code.",
                )
                return redirect("accounts:verify")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


def verify_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    pending_email = request.session.get(PENDING_EMAIL_SESSION_KEY, "")

    if request.method == "POST":
        form = OTPVerificationForm(request.POST, prefix="verify")
        if form.is_valid():
            try:
                verify_registration_otp(**form.cleaned_data)
            except OTPAlreadyVerifiedError:
                request.session.pop(PENDING_EMAIL_SESSION_KEY, None)
                messages.info(request, "This account is already verified. You can sign in.")
                return redirect("accounts:login")
            except AccountServiceError as exc:
                form.add_error("code", str(exc))
            else:
                request.session.pop(PENDING_EMAIL_SESSION_KEY, None)
                messages.success(request, "Email verified. You can now sign in.")
                return redirect("accounts:login")
        resend_form = OTPResendForm(
            prefix="resend",
            initial={"email": pending_email},
        )
    else:
        form = OTPVerificationForm(
            prefix="verify",
            initial={"email": pending_email},
        )
        resend_form = OTPResendForm(
            prefix="resend",
            initial={"email": pending_email},
        )

    return render(
        request,
        "accounts/verify.html",
        _verification_context(
            verification_form=form,
            resend_form=resend_form,
        ),
    )


@require_POST
def resend_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    form = OTPResendForm(request.POST, prefix="resend")
    if not form.is_valid():
        messages.error(request, "Enter a valid email address.")
        return redirect("accounts:verify")

    email = form.cleaned_data["email"]
    request.session[PENDING_EMAIL_SESSION_KEY] = email

    try:
        resend_registration_otp(email=email)
    except OTPThrottleError as exc:
        messages.error(
            request,
            f"{exc} Retry in about {exc.retry_after} seconds.",
        )
    except OTPEmailDeliveryError:
        messages.warning(
            request,
            ("A new code was created, but the email could not be delivered. Try again later."),
        )
    except AccountServiceError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "A new verification code was sent.")

    return redirect("accounts:verify")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            try:
                login_user(
                    request,
                    username=form.cleaned_data["username"],
                    password=form.cleaned_data["password"],
                )
            except AccountServiceError as exc:
                form.add_error(None, str(exc))
            else:
                return redirect(_safe_next_url(request, form.cleaned_data.get("next")))
    else:
        form = LoginForm(initial={"next": request.GET.get("next", "")})

    return render(request, "accounts/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout_user(request)
    messages.success(request, "You have signed out.")
    return redirect("core:home")


@login_required
def current_user_view(request):
    return render(request, "accounts/me.html")
