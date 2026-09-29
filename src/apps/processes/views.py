from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import ProcessManagementForm, ProcessStepManagementForm
from .models import Process
from .selectors import (
    get_process_for_owner,
    get_process_step_for_owner,
    get_process_steps_for_owner,
    get_processes_for_owner,
)
from .services import (
    PROCESS_NOT_DRAFT_MESSAGE,
    STEP_NOT_DRAFT_MESSAGE,
    close_process,
    create_process,
    create_process_step,
    delete_draft_process,
    delete_process_step,
    publish_process,
    reorder_process_steps,
    update_draft_process,
)


def _owned_process_or_404(*, owner, process_id):
    process = get_process_for_owner(owner=owner, process_id=process_id)
    if process is None:
        raise Http404
    return process


def _owned_step_or_404(*, owner, process_id, step_id):
    step = get_process_step_for_owner(
        owner=owner,
        process_id=process_id,
        step_id=step_id,
    )
    if step is None:
        raise Http404
    return step


def _add_validation_errors(form, exc):
    if hasattr(exc, "message_dict"):
        errors = exc.message_dict
    else:
        errors = {"__all__": exc.messages}

    for field, error_list in errors.items():
        target = field if field in form.fields else None
        for error in error_list:
            form.add_error(target, error)


def _first_validation_message(exc):
    if hasattr(exc, "message_dict"):
        for error_list in exc.message_dict.values():
            if error_list:
                return error_list[0]
    return exc.messages[0] if exc.messages else "The operation could not be completed."


@login_required
def process_list(request):
    processes = get_processes_for_owner(owner=request.user)
    return render(request, "processes/manage/list.html", {"processes": processes})


@login_required
def process_detail(request, process_id):
    process = _owned_process_or_404(owner=request.user, process_id=process_id)
    return render(
        request,
        "processes/manage/detail.html",
        {"managed_process": process},
    )


@login_required
def process_create(request):
    if request.method == "POST":
        form = ProcessManagementForm(request.POST, owner=request.user)
        if form.is_valid():
            category = form.cleaned_data["category"]
            try:
                managed_process = create_process(
                    owner=request.user,
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data["description"],
                    category_id=category.pk if category else None,
                    process_type=form.cleaned_data["process_type"],
                    visibility=form.cleaned_data["visibility"],
                    access_password=form.cleaned_data["access_password"] or None,
                )
            except ValidationError as exc:
                _add_validation_errors(form, exc)
            else:
                messages.success(request, "Process created as a draft.")
                return redirect("processes:detail", process_id=managed_process.pk)
    else:
        form = ProcessManagementForm(owner=request.user)

    return render(
        request,
        "processes/manage/form.html",
        {
            "form": form,
            "page_title": "Create process",
            "submit_label": "Create draft",
        },
    )


@login_required
def process_update(request, process_id):
    managed_process = _owned_process_or_404(owner=request.user, process_id=process_id)
    if managed_process.status != Process.Status.DRAFT:
        messages.error(request, PROCESS_NOT_DRAFT_MESSAGE)
        return redirect("processes:detail", process_id=managed_process.pk)

    if request.method == "POST":
        form = ProcessManagementForm(request.POST, owner=request.user)
        if form.is_valid():
            category = form.cleaned_data["category"]
            try:
                managed_process = update_draft_process(
                    process=managed_process,
                    owner=request.user,
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data["description"],
                    category_id=category.pk if category else None,
                    process_type=form.cleaned_data["process_type"],
                    visibility=form.cleaned_data["visibility"],
                    access_password=form.cleaned_data["access_password"] or None,
                )
            except ValidationError as exc:
                _add_validation_errors(form, exc)
            else:
                messages.success(request, "Draft process updated.")
                return redirect("processes:detail", process_id=managed_process.pk)
    else:
        form = ProcessManagementForm(
            owner=request.user,
            initial={
                "title": managed_process.title,
                "description": managed_process.description,
                "category": managed_process.category_id,
                "process_type": managed_process.process_type,
                "visibility": managed_process.visibility,
            },
        )

    return render(
        request,
        "processes/manage/form.html",
        {
            "form": form,
            "managed_process": managed_process,
            "page_title": "Edit process",
            "submit_label": "Save changes",
        },
    )


@login_required
@require_POST
def process_publish(request, process_id):
    managed_process = _owned_process_or_404(owner=request.user, process_id=process_id)
    try:
        managed_process = publish_process(
            process=managed_process,
            owner=request.user,
        )
    except ValidationError as exc:
        messages.error(request, _first_validation_message(exc))
    else:
        messages.success(
            request,
            "Process published. Its execution definition is now immutable.",
        )
    return redirect("processes:detail", process_id=managed_process.pk)


@login_required
@require_POST
def process_close(request, process_id):
    managed_process = _owned_process_or_404(owner=request.user, process_id=process_id)
    try:
        managed_process = close_process(
            process=managed_process,
            owner=request.user,
        )
    except ValidationError as exc:
        messages.error(request, _first_validation_message(exc))
    else:
        messages.success(request, "Process closed.")
    return redirect("processes:detail", process_id=managed_process.pk)


@login_required
def process_delete(request, process_id):
    managed_process = _owned_process_or_404(owner=request.user, process_id=process_id)
    if managed_process.status != Process.Status.DRAFT:
        messages.error(request, PROCESS_NOT_DRAFT_MESSAGE)
        return redirect("processes:detail", process_id=managed_process.pk)

    if request.method == "POST":
        try:
            delete_draft_process(process=managed_process, owner=request.user)
        except ValidationError as exc:
            messages.error(request, _first_validation_message(exc))
            return redirect("processes:detail", process_id=managed_process.pk)

        messages.success(request, "Draft process deleted.")
        return redirect("processes:list")

    return render(
        request,
        "processes/manage/confirm_delete.html",
        {"managed_process": managed_process},
    )


@login_required
def process_builder(request, process_id):
    managed_process = _owned_process_or_404(owner=request.user, process_id=process_id)
    steps = get_process_steps_for_owner(
        owner=request.user,
        process_id=managed_process.pk,
    )
    return render(
        request,
        "processes/builder/index.html",
        {
            "managed_process": managed_process,
            "steps": steps,
            "can_edit": managed_process.status == Process.Status.DRAFT,
        },
    )


@login_required
def process_step_create(request, process_id):
    managed_process = _owned_process_or_404(owner=request.user, process_id=process_id)
    if managed_process.status != Process.Status.DRAFT:
        messages.error(request, STEP_NOT_DRAFT_MESSAGE)
        return redirect("processes:builder", process_id=managed_process.pk)

    if request.method == "POST":
        form = ProcessStepManagementForm(
            request.POST,
            owner=request.user,
            process=managed_process,
        )
        if form.is_valid():
            selected_form = form.cleaned_data["form"]
            try:
                create_process_step(
                    process=managed_process,
                    owner=request.user,
                    form_id=selected_form.pk,
                )
            except ValidationError as exc:
                _add_validation_errors(form, exc)
            else:
                messages.success(request, "Process step added.")
                return redirect("processes:builder", process_id=managed_process.pk)
    else:
        form = ProcessStepManagementForm(
            owner=request.user,
            process=managed_process,
        )

    return render(
        request,
        "processes/builder/step_form.html",
        {
            "form": form,
            "managed_process": managed_process,
        },
    )


@login_required
@require_POST
def process_step_delete(request, process_id, step_id):
    managed_process = _owned_process_or_404(owner=request.user, process_id=process_id)
    _owned_step_or_404(
        owner=request.user,
        process_id=process_id,
        step_id=step_id,
    )
    try:
        delete_process_step(
            process=managed_process,
            owner=request.user,
            step_id=step_id,
        )
    except ValidationError as exc:
        messages.error(request, _first_validation_message(exc))
    else:
        messages.success(request, "Process step removed and ordering repaired.")
    return redirect("processes:builder", process_id=managed_process.pk)


@login_required
@require_POST
def process_step_move(request, process_id, step_id, direction):
    if direction not in {"up", "down"}:
        raise Http404

    managed_process = _owned_process_or_404(owner=request.user, process_id=process_id)
    _owned_step_or_404(
        owner=request.user,
        process_id=process_id,
        step_id=step_id,
    )

    steps = list(
        get_process_steps_for_owner(
            owner=request.user,
            process_id=managed_process.pk,
        )
    )
    step_ids = [step.pk for step in steps]
    index = step_ids.index(step_id)
    target = index - 1 if direction == "up" else index + 1

    if 0 <= target < len(step_ids):
        step_ids[index], step_ids[target] = step_ids[target], step_ids[index]
        try:
            reorder_process_steps(
                process=managed_process,
                owner=request.user,
                step_ids=step_ids,
            )
        except ValidationError as exc:
            messages.error(request, _first_validation_message(exc))

    return redirect("processes:builder", process_id=managed_process.pk)
