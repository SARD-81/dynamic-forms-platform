from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
    require_POST,
    require_safe,
)

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
from apps.forms.participant_presentation import html_submission_answers, participant_form_context
from apps.forms.participant_selectors import get_form_participant_read_model

from .models import Process, ProcessStepRun
from .participant_selectors import (
    RESOURCE_TYPE,
    get_executable_process_by_public_id,
    get_in_progress_process_run_for_respondent,
    get_process_participant_read_model,
    get_process_run_by_token_hash,
    get_process_run_for_process,
    get_published_process_by_public_id,
    increment_process_view_count,
)
from .services import complete_process_step_run, hash_resume_token, start_process_run

RUN_GRANTS_SESSION_KEY = "process_run_browser_grants"
RUN_TOKEN_ONCE_SESSION_KEY = "process_run_resume_token_once"


def _published_process_or_404(*, public_id):
    process = get_published_process_by_public_id(public_id=public_id)
    if process is None:
        raise Http404
    return process


def _executable_process_or_404(*, public_id):
    process = get_executable_process_by_public_id(public_id=public_id)
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


def _run_grant_key(*, process, run):
    return f"{process.public_id}:{run.public_id}"


def _grant_anonymous_run(*, session, process, run):
    grants = dict(session.get(RUN_GRANTS_SESSION_KEY, {}))
    grants[_run_grant_key(process=process, run=run)] = True
    session[RUN_GRANTS_SESSION_KEY] = grants
    session.modified = True


def _has_anonymous_run_grant(*, session, process, run):
    grants = session.get(RUN_GRANTS_SESSION_KEY, {})
    return grants.get(_run_grant_key(process=process, run=run)) is True


def _remember_resume_token_once(*, session, process, run, raw_token):
    tokens = dict(session.get(RUN_TOKEN_ONCE_SESSION_KEY, {}))
    tokens[_run_grant_key(process=process, run=run)] = raw_token
    session[RUN_TOKEN_ONCE_SESSION_KEY] = tokens
    session.modified = True


def _pop_resume_token_once(*, session, process, run):
    tokens = dict(session.get(RUN_TOKEN_ONCE_SESSION_KEY, {}))
    key = _run_grant_key(process=process, run=run)
    raw_token = tokens.pop(key, None)
    if raw_token is not None:
        session[RUN_TOKEN_ONCE_SESSION_KEY] = tokens
        session.modified = True
    return raw_token


def _run_is_authorized(*, request, process, run):
    if run.respondent_id is not None:
        return request.user.is_authenticated and request.user.pk == run.respondent_id
    return _has_anonymous_run_grant(
        session=request.session,
        process=process,
        run=run,
    )


def _unlock_context(*, public_id, error=None, next_action="detail"):
    context = {
        "resource_type_label": "process",
        "unlock_url": "processes_participant:unlock",
        "public_id": public_id,
        "unlock_next": next_action,
    }
    if error:
        context["unlock_error"] = error
    return context


def _rate_limited_response(request, *, public_id, next_action="detail"):
    response = render(
        request,
        "participants/unlock.html",
        _unlock_context(
            public_id=public_id,
            error="Too many password attempts. Try again later.",
            next_action=next_action,
        ),
        status=429,
    )
    response["Retry-After"] = str(participant_unlock_retry_after_seconds())
    return response


def _temporarily_unavailable_response(request, *, public_id, next_action="detail"):
    return render(
        request,
        "participants/unlock.html",
        _unlock_context(
            public_id=public_id,
            error="Password verification is temporarily unavailable. Try again later.",
            next_action=next_action,
        ),
        status=503,
    )


def _ordered_step_runs(run):
    return list(run.step_runs.all())


def _run_context(*, process, run, resume_token_once=None, execution_error=None):
    step_runs = _ordered_step_runs(run)
    completed_count = sum(step.status == ProcessStepRun.Status.COMPLETED for step in step_runs)
    return {
        "participant_process": process,
        "process_run": run,
        "step_runs": step_runs,
        "completed_step_count": completed_count,
        "total_step_count": len(step_runs),
        "resume_token_once": resume_token_once,
        "execution_error": execution_error,
    }


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
    current_run = get_in_progress_process_run_for_respondent(
        process=process,
        respondent=request.user if request.user.is_authenticated else None,
    )
    if request.method == "GET":
        increment_process_view_count(process_id=process.pk)
    return render(
        request,
        "participants/process_detail.html",
        {
            "participant_process": read_model,
            "current_run": current_run,
        },
    )


@require_POST
def participant_process_unlock(request, public_id):
    next_action = request.POST.get("next", "detail")
    if next_action not in {"detail", "resume"}:
        next_action = "detail"

    if next_action == "resume":
        process = _executable_process_or_404(public_id=public_id)
    else:
        process = _published_process_or_404(public_id=public_id)

    if process.visibility == Process.Visibility.PUBLIC:
        target = (
            "processes_participant:resume"
            if next_action == "resume"
            else "processes_participant:detail"
        )
        return redirect(target, public_id=process.public_id)

    client_id = participant_client_id(request)
    limit_args = {
        "session": request.session,
        "resource_type": RESOURCE_TYPE,
        "public_id": process.public_id,
        "client_id": client_id,
    }
    try:
        if reserve_participant_unlock_attempt(**limit_args):
            return _rate_limited_response(
                request,
                public_id=process.public_id,
                next_action=next_action,
            )
    except ParticipantUnlockThrottleUnavailable:
        return _temporarily_unavailable_response(
            request,
            public_id=process.public_id,
            next_action=next_action,
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
                next_action=next_action,
            ),
            status=403,
        )

    try:
        clear_participant_unlock_failures(**limit_args)
    except ParticipantUnlockThrottleUnavailable:
        return _temporarily_unavailable_response(
            request,
            public_id=process.public_id,
            next_action=next_action,
        )

    grant_participant_access(
        session=request.session,
        resource_type=RESOURCE_TYPE,
        public_id=process.public_id,
    )
    target = (
        "processes_participant:resume"
        if next_action == "resume"
        else "processes_participant:detail"
    )
    return redirect(target, public_id=process.public_id)


@require_POST
def participant_process_run_start(request, public_id):
    process = _published_process_or_404(public_id=public_id)
    if not _has_access(request=request, process=process):
        return render(
            request,
            "participants/unlock.html",
            _unlock_context(public_id=process.public_id),
            status=403,
        )

    respondent = request.user if request.user.is_authenticated else None
    try:
        run, raw_token = start_process_run(
            process=process,
            respondent=respondent,
        )
    except ValidationError as exc:
        errors = exc.message_dict if hasattr(exc, "message_dict") else {"process": exc.messages}
        read_model = get_process_participant_read_model(process=process)
        return render(
            request,
            "participants/process_detail.html",
            {
                "participant_process": read_model,
                "current_run": None,
                "execution_errors": [
                    message for messages in errors.values() for message in messages
                ],
            },
            status=400,
        )

    if raw_token is not None:
        _grant_anonymous_run(
            session=request.session,
            process=process,
            run=run,
        )
        _remember_resume_token_once(
            session=request.session,
            process=process,
            run=run,
            raw_token=raw_token,
        )

    return redirect(
        "processes_participant:run_detail",
        public_id=process.public_id,
        run_public_id=run.public_id,
    )


@require_http_methods(["GET", "POST"])
def participant_process_resume(request, public_id):
    process = _executable_process_or_404(public_id=public_id)
    if not _has_access(request=request, process=process):
        return render(
            request,
            "participants/unlock.html",
            _unlock_context(
                public_id=process.public_id,
                next_action="resume",
            ),
            status=403,
        )

    if request.method == "GET" and request.user.is_authenticated:
        current_run = get_in_progress_process_run_for_respondent(
            process=process,
            respondent=request.user,
        )
        if current_run is not None:
            return redirect(
                "processes_participant:run_detail",
                public_id=process.public_id,
                run_public_id=current_run.public_id,
            )

    error = None
    if request.method == "POST":
        raw_token = request.POST.get("resume_token", "").strip()
        run = None
        if raw_token:
            run = get_process_run_by_token_hash(
                process=process,
                resume_token_hash=hash_resume_token(raw_token),
            )
        if run is None:
            error = "That resume token is not valid for this process."
        else:
            _grant_anonymous_run(
                session=request.session,
                process=process,
                run=run,
            )
            return redirect(
                "processes_participant:run_detail",
                public_id=process.public_id,
                run_public_id=run.public_id,
            )

    return render(
        request,
        "participants/process_resume.html",
        {
            "participant_process": process,
            "resume_error": error,
        },
        status=400 if error else 200,
    )


@never_cache
@require_GET
def participant_process_run_detail(request, public_id, run_public_id):
    process = _executable_process_or_404(public_id=public_id)
    if not _has_access(request=request, process=process):
        return render(
            request,
            "participants/unlock.html",
            _unlock_context(
                public_id=process.public_id,
                next_action="resume",
            ),
            status=403,
        )

    run = get_process_run_for_process(
        process=process,
        run_public_id=run_public_id,
    )
    if run is None:
        raise Http404
    if not _run_is_authorized(request=request, process=process, run=run):
        return render(
            request,
            "participants/process_resume.html",
            {
                "participant_process": process,
                "resume_error": "Resume this run with its token to continue.",
            },
            status=403,
        )

    resume_token_once = _pop_resume_token_once(
        session=request.session,
        process=process,
        run=run,
    )
    return render(
        request,
        "participants/process_run_detail.html",
        _run_context(
            process=process,
            run=run,
            resume_token_once=resume_token_once,
        ),
    )


@require_http_methods(["GET", "POST"])
def participant_process_step(request, public_id, run_public_id, step_id):
    process = _executable_process_or_404(public_id=public_id)
    if not _has_access(request=request, process=process):
        return render(
            request,
            "participants/unlock.html",
            _unlock_context(
                public_id=process.public_id,
                next_action="resume",
            ),
            status=403,
        )

    run = get_process_run_for_process(
        process=process,
        run_public_id=run_public_id,
    )
    if run is None:
        raise Http404
    if not _run_is_authorized(request=request, process=process, run=run):
        return render(
            request,
            "participants/process_resume.html",
            {
                "participant_process": process,
                "resume_error": "Resume this run with its token to continue.",
            },
            status=403,
        )

    step_run = next(
        (
            candidate
            for candidate in _ordered_step_runs(run)
            if candidate.process_step_id == step_id
        ),
        None,
    )
    if step_run is None:
        raise Http404

    if step_run.status == ProcessStepRun.Status.COMPLETED:
        return redirect(
            "processes_participant:run_detail",
            public_id=process.public_id,
            run_public_id=run.public_id,
        )

    form = step_run.process_step.form
    if step_run.status != ProcessStepRun.Status.AVAILABLE:
        return render(
            request,
            "participants/process_step.html",
            {
                "participant_process": process,
                "process_run": run,
                "step_run": step_run,
                "step_error": "This step is locked until the required earlier step is complete.",
            },
            status=409,
        )

    if form.status != form.Status.PUBLISHED:
        return render(
            request,
            "participants/process_step.html",
            {
                "participant_process": process,
                "process_run": run,
                "step_run": step_run,
                "step_error": "This step is temporarily unavailable because its form is closed.",
            },
            status=409,
        )

    read_model = get_form_participant_read_model(form=form)
    validation_errors = None

    if request.method == "POST":
        try:
            answers = html_submission_answers(
                read_model=read_model,
                post_data=request.POST,
            )
            complete_process_step_run(
                process_run=run,
                step_run_id=step_run.pk,
                answers=answers,
            )
        except ValidationError as exc:
            validation_errors = (
                exc.message_dict if hasattr(exc, "message_dict") else {"answers": exc.messages}
            )
        else:
            return redirect(
                "processes_participant:run_detail",
                public_id=process.public_id,
                run_public_id=run.public_id,
            )

    context = participant_form_context(
        read_model=read_model,
        post_data=request.POST if request.method == "POST" else None,
        validation_errors=validation_errors,
    )
    context.update(
        {
            "participant_process": process,
            "process_run": run,
            "step_run": step_run,
        }
    )
    return render(
        request,
        "participants/process_step.html",
        context,
        status=400 if validation_errors else 200,
    )
