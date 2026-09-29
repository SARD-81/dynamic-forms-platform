from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST, require_safe

from apps.core.participant_access import (
    clear_participant_unlock_failures,
    grant_participant_access,
    has_participant_grant,
    ParticipantUnlockThrottleUnavailable,
    participant_client_id,
    participant_unlock_retry_after_seconds,
    reserve_participant_unlock_attempt,
    verify_participant_password,
)

from .models import Process
from .participant_selectors import (
    RESOURCE_TYPE,
    get_process_participant_read_model,
    get_published_process_by_public_id,
    increment_process_view_count,
)


def _published_process_or_404(*, public_id):
    process = get_published_process_by_public_id(public_id=public_id)
    if process is None:
        raise Http404
    return process


def _has_access(*, request, process):
    if process.visibility == Process.Visibility.PUBLIC:
        return True
    return has_participant_grant(
        session=request.session,
        resource_type=RESOURCE_TYPE,
        public_id=process.public_id,
    )


def _unlock_context(*, public_id, error=None):
    context = {
        "resource_type_label": "process",
        "unlock_url": "processes_participant:unlock",
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
def participant_process_detail(request, public_id):
    process = _published_process_or_404(public_id=public_id)
    if not _has_access(request=request, process=process):
        return render(
            request,
            "participants/unlock.html",
            _unlock_context(public_id=process.public_id),
            status=403,
        )

    read_model = get_process_participant_read_model(process=process)
    if request.method == "GET":
        increment_process_view_count(process_id=process.pk)
    return render(
        request,
        "participants/process_detail.html",
        {"participant_process": read_model},
    )


@require_POST
def participant_process_unlock(request, public_id):
    process = _published_process_or_404(public_id=public_id)

    if process.visibility == Process.Visibility.PUBLIC:
        return redirect("processes_participant:detail", public_id=process.public_id)

    client_id = participant_client_id(request)
    limit_args = {
        "session": request.session,
        "resource_type": RESOURCE_TYPE,
        "public_id": process.public_id,
        "client_id": client_id,
    }
    try:
        if reserve_participant_unlock_attempt(**limit_args):
            return _rate_limited_response(request, public_id=process.public_id)
    except ParticipantUnlockThrottleUnavailable:
        return _temporarily_unavailable_response(
            request,
            public_id=process.public_id,
        )

    password = request.POST.get("password", "")
    if not verify_participant_password(
        password_hash=process.access_password_hash,
        password=password,
    ):
        return render(
            request,
            "participants/unlock.html",
            _unlock_context(
                public_id=process.public_id,
                error="The password is incorrect.",
            ),
            status=403,
        )

    try:
        clear_participant_unlock_failures(**limit_args)
    except ParticipantUnlockThrottleUnavailable:
        return _temporarily_unavailable_response(
            request,
            public_id=process.public_id,
        )
    grant_participant_access(
        session=request.session,
        resource_type=RESOURCE_TYPE,
        public_id=process.public_id,
    )
    return redirect("processes_participant:detail", public_id=process.public_id)
