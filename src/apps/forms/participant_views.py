from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST, require_safe

from apps.core.participant_access import (
    ParticipantUnlockThrottleUnavailable,
    clear_participant_unlock_failures,
    grant_participant_access,
    has_participant_grant,
    participant_client_id,
    participant_unlock_retry_after_seconds,
    reserve_participant_unlock_attempt,
    verify_participant_password,
)

from .models import Form
from .participant_selectors import (
    RESOURCE_TYPE,
    get_form_participant_read_model,
    get_published_form_by_public_id,
    increment_form_view_count,
)


def _published_form_or_404(*, public_id):
    form = get_published_form_by_public_id(public_id=public_id)
    if form is None:
        raise Http404
    return form


def _has_access(*, request, form):
    if form.visibility == Form.Visibility.PUBLIC:
        return True
    return has_participant_grant(
        session=request.session,
        resource_type=RESOURCE_TYPE,
        public_id=form.public_id,
    )


def _unlock_context(*, public_id, error=None):
    context = {
        "resource_type_label": "form",
        "unlock_url": "forms_participant:unlock",
        "public_id": public_id,
    }
    if error:
        context["unlock_error"] = error
    return context


def _rate_limited_response(request, *, public_id):
    response = render(
        request,
        "participants/unlock.html",
        _unlock_context(
            public_id=public_id,
            error="Too many password attempts. Try again later.",
        ),
        status=429,
    )
    response["Retry-After"] = str(participant_unlock_retry_after_seconds())
    return response


def _temporarily_unavailable_response(request, *, public_id):
    return render(
        request,
        "participants/unlock.html",
        _unlock_context(
            public_id=public_id,
            error="Password verification is temporarily unavailable. Try again later.",
        ),
        status=503,
    )


@require_safe
def participant_form_detail(request, public_id):
    form = _published_form_or_404(public_id=public_id)
    if not _has_access(request=request, form=form):
        return render(
            request,
            "participants/unlock.html",
            _unlock_context(public_id=form.public_id),
            status=403,
        )

    read_model = get_form_participant_read_model(form=form)
    if request.method == "GET":
        increment_form_view_count(form_id=form.pk)
    return render(
        request,
        "participants/form_detail.html",
        {"participant_form": read_model},
    )


@require_POST
def participant_form_unlock(request, public_id):
    form = _published_form_or_404(public_id=public_id)

    if form.visibility == Form.Visibility.PUBLIC:
        return redirect("forms_participant:detail", public_id=form.public_id)

    client_id = participant_client_id(request)
    limit_args = {
        "session": request.session,
        "resource_type": RESOURCE_TYPE,
        "public_id": form.public_id,
        "client_id": client_id,
    }
    try:
        if reserve_participant_unlock_attempt(**limit_args):
            return _rate_limited_response(request, public_id=form.public_id)
    except ParticipantUnlockThrottleUnavailable:
        return _temporarily_unavailable_response(
            request,
            public_id=form.public_id,
        )

    password = request.POST.get("password", "")
    if not verify_participant_password(
        password_hash=form.access_password_hash,
        password=password,
    ):
        return render(
            request,
            "participants/unlock.html",
            _unlock_context(
                public_id=form.public_id,
                error="The password is incorrect.",
            ),
            status=403,
        )

    try:
        clear_participant_unlock_failures(**limit_args)
    except ParticipantUnlockThrottleUnavailable:
        return _temporarily_unavailable_response(
            request,
            public_id=form.public_id,
        )
    grant_participant_access(
        session=request.session,
        resource_type=RESOURCE_TYPE,
        public_id=form.public_id,
    )
    return redirect("forms_participant:detail", public_id=form.public_id)
