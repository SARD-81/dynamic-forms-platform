from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.core.integrations import form_has_active_process_runs

from .forms import FormManagementForm, QuestionManagementForm, QuestionOptionForm
from .models import Form
from .selectors import (
    get_form_for_owner,
    get_forms_for_owner,
    get_option_for_owner,
    get_question_for_owner,
    get_questions_for_form_owner,
)
from .services import (
    FORM_NOT_DRAFT_MESSAGE,
    SCHEMA_NOT_DRAFT_MESSAGE,
    close_form,
    create_form,
    create_question,
    create_question_option,
    delete_draft_form,
    delete_question,
    delete_question_option,
    move_question,
    move_question_option,
    publish_form,
    update_draft_form,
    update_question,
    update_question_option,
)


def _owned_form_or_404(*, owner, form_id):
    form = get_form_for_owner(owner=owner, form_id=form_id)
    if form is None:
        raise Http404
    return form


def _owned_question_or_404(*, owner, form_id, question_id):
    question = get_question_for_owner(
        owner=owner,
        form_id=form_id,
        question_id=question_id,
    )
    if question is None:
        raise Http404
    return question


def _owned_option_or_404(*, owner, form_id, question_id, option_id):
    option = get_option_for_owner(
        owner=owner,
        form_id=form_id,
        question_id=question_id,
        option_id=option_id,
    )
    if option is None:
        raise Http404
    return option


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
def form_list(request):
    forms = get_forms_for_owner(owner=request.user)
    return render(request, "forms/manage/list.html", {"forms": forms})


@login_required
def form_detail(request, form_id):
    form = _owned_form_or_404(owner=request.user, form_id=form_id)
    return render(request, "forms/manage/detail.html", {"managed_form": form})


@login_required
def form_create(request):
    if request.method == "POST":
        form = FormManagementForm(request.POST, owner=request.user)
        if form.is_valid():
            category = form.cleaned_data["category"]
            try:
                managed_form = create_form(
                    owner=request.user,
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data["description"],
                    category_id=category.pk if category else None,
                    visibility=form.cleaned_data["visibility"],
                    access_password=form.cleaned_data["access_password"] or None,
                )
            except ValidationError as exc:
                _add_validation_errors(form, exc)
            else:
                messages.success(request, "Form created as a draft.")
                return redirect("forms:detail", form_id=managed_form.pk)
    else:
        form = FormManagementForm(owner=request.user)

    return render(
        request,
        "forms/manage/form.html",
        {
            "form": form,
            "page_title": "Create form",
            "submit_label": "Create draft",
        },
    )


@login_required
def form_update(request, form_id):
    managed_form = _owned_form_or_404(owner=request.user, form_id=form_id)
    if managed_form.status != Form.Status.DRAFT:
        messages.error(request, FORM_NOT_DRAFT_MESSAGE)
        return redirect("forms:detail", form_id=managed_form.pk)

    if request.method == "POST":
        form = FormManagementForm(request.POST, owner=request.user)
        if form.is_valid():
            category = form.cleaned_data["category"]
            try:
                managed_form = update_draft_form(
                    form=managed_form,
                    owner=request.user,
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data["description"],
                    category_id=category.pk if category else None,
                    visibility=form.cleaned_data["visibility"],
                    access_password=form.cleaned_data["access_password"] or None,
                )
            except ValidationError as exc:
                _add_validation_errors(form, exc)
            else:
                messages.success(request, "Draft form updated.")
                return redirect("forms:detail", form_id=managed_form.pk)
    else:
        form = FormManagementForm(
            owner=request.user,
            initial={
                "title": managed_form.title,
                "description": managed_form.description,
                "category": managed_form.category_id,
                "visibility": managed_form.visibility,
            },
        )

    return render(
        request,
        "forms/manage/form.html",
        {
            "form": form,
            "managed_form": managed_form,
            "page_title": "Edit form",
            "submit_label": "Save changes",
        },
    )


@login_required
@require_POST
def form_publish(request, form_id):
    managed_form = _owned_form_or_404(owner=request.user, form_id=form_id)
    try:
        managed_form = publish_form(form=managed_form, owner=request.user)
    except ValidationError as exc:
        messages.error(request, _first_validation_message(exc))
    else:
        messages.success(request, "Form published. Its definition is now immutable.")
    return redirect("forms:detail", form_id=managed_form.pk)


@login_required
@require_POST
def form_close(request, form_id):
    managed_form = _owned_form_or_404(owner=request.user, form_id=form_id)
    try:
        managed_form = close_form(
            form=managed_form,
            owner=request.user,
            active_run_checker=form_has_active_process_runs,
        )
    except ValidationError as exc:
        messages.error(request, _first_validation_message(exc))
    else:
        messages.success(request, "Form closed.")
    return redirect("forms:detail", form_id=managed_form.pk)


@login_required
def form_delete(request, form_id):
    managed_form = _owned_form_or_404(owner=request.user, form_id=form_id)
    if managed_form.status != Form.Status.DRAFT:
        messages.error(request, FORM_NOT_DRAFT_MESSAGE)
        return redirect("forms:detail", form_id=managed_form.pk)

    if request.method == "POST":
        try:
            delete_draft_form(form=managed_form, owner=request.user)
        except ValidationError as exc:
            messages.error(request, _first_validation_message(exc))
            return redirect("forms:detail", form_id=managed_form.pk)

        messages.success(request, "Draft form deleted.")
        return redirect("forms:list")

    return render(
        request,
        "forms/manage/confirm_delete.html",
        {"managed_form": managed_form},
    )


@login_required
def form_builder(request, form_id):
    managed_form = _owned_form_or_404(owner=request.user, form_id=form_id)
    questions = get_questions_for_form_owner(owner=request.user, form_id=form_id)
    return render(
        request,
        "forms/builder/index.html",
        {
            "managed_form": managed_form,
            "questions": questions,
            "can_edit": managed_form.status == Form.Status.DRAFT,
        },
    )


@login_required
def question_create(request, form_id):
    managed_form = _owned_form_or_404(owner=request.user, form_id=form_id)
    if managed_form.status != Form.Status.DRAFT:
        messages.error(request, SCHEMA_NOT_DRAFT_MESSAGE)
        return redirect("forms:builder", form_id=form_id)

    if request.method == "POST":
        form = QuestionManagementForm(request.POST)
        if form.is_valid():
            try:
                create_question(
                    form=managed_form,
                    owner=request.user,
                    **form.cleaned_data,
                )
            except ValidationError as exc:
                _add_validation_errors(form, exc)
            else:
                messages.success(request, "Question added.")
                return redirect("forms:builder", form_id=form_id)
    else:
        form = QuestionManagementForm()

    return render(
        request,
        "forms/builder/question_form.html",
        {
            "form": form,
            "managed_form": managed_form,
            "page_title": "Add question",
            "submit_label": "Add question",
        },
    )


@login_required
def question_update(request, form_id, question_id):
    managed_form = _owned_form_or_404(owner=request.user, form_id=form_id)
    question = _owned_question_or_404(
        owner=request.user,
        form_id=form_id,
        question_id=question_id,
    )
    if managed_form.status != Form.Status.DRAFT:
        messages.error(request, SCHEMA_NOT_DRAFT_MESSAGE)
        return redirect("forms:builder", form_id=form_id)

    if request.method == "POST":
        form = QuestionManagementForm(request.POST)
        if form.is_valid():
            try:
                update_question(
                    question=question,
                    owner=request.user,
                    **form.cleaned_data,
                )
            except ValidationError as exc:
                _add_validation_errors(form, exc)
            else:
                messages.success(request, "Question updated.")
                return redirect("forms:builder", form_id=form_id)
    else:
        form = QuestionManagementForm(
            initial={
                "text": question.text,
                "question_type": question.question_type,
                "is_required": question.is_required,
                "max_length": question.max_length,
                "min_value": question.min_value,
                "max_value": question.max_value,
            }
        )

    return render(
        request,
        "forms/builder/question_form.html",
        {
            "form": form,
            "managed_form": managed_form,
            "question": question,
            "page_title": "Edit question",
            "submit_label": "Save question",
        },
    )


@login_required
@require_POST
def question_delete(request, form_id, question_id):
    question = _owned_question_or_404(
        owner=request.user,
        form_id=form_id,
        question_id=question_id,
    )
    try:
        delete_question(question=question, owner=request.user)
    except ValidationError as exc:
        messages.error(request, _first_validation_message(exc))
    else:
        messages.success(request, "Question deleted and ordering repaired.")
    return redirect("forms:builder", form_id=form_id)


@login_required
@require_POST
def question_move(request, form_id, question_id, direction):
    question = _owned_question_or_404(
        owner=request.user,
        form_id=form_id,
        question_id=question_id,
    )
    try:
        move_question(question=question, owner=request.user, direction=direction)
    except ValidationError as exc:
        messages.error(request, _first_validation_message(exc))
    return redirect("forms:builder", form_id=form_id)


@login_required
def option_create(request, form_id, question_id):
    managed_form = _owned_form_or_404(owner=request.user, form_id=form_id)
    question = _owned_question_or_404(
        owner=request.user,
        form_id=form_id,
        question_id=question_id,
    )
    if managed_form.status != Form.Status.DRAFT:
        messages.error(request, SCHEMA_NOT_DRAFT_MESSAGE)
        return redirect("forms:builder", form_id=form_id)

    if request.method == "POST":
        form = QuestionOptionForm(request.POST)
        if form.is_valid():
            try:
                create_question_option(
                    question=question,
                    owner=request.user,
                    label=form.cleaned_data["label"],
                )
            except ValidationError as exc:
                _add_validation_errors(form, exc)
            else:
                messages.success(request, "Option added.")
                return redirect("forms:builder", form_id=form_id)
    else:
        form = QuestionOptionForm()

    return render(
        request,
        "forms/builder/option_form.html",
        {
            "form": form,
            "managed_form": managed_form,
            "question": question,
            "page_title": "Add option",
            "submit_label": "Add option",
        },
    )


@login_required
def option_update(request, form_id, question_id, option_id):
    managed_form = _owned_form_or_404(owner=request.user, form_id=form_id)
    question = _owned_question_or_404(
        owner=request.user,
        form_id=form_id,
        question_id=question_id,
    )
    option = _owned_option_or_404(
        owner=request.user,
        form_id=form_id,
        question_id=question_id,
        option_id=option_id,
    )
    if managed_form.status != Form.Status.DRAFT:
        messages.error(request, SCHEMA_NOT_DRAFT_MESSAGE)
        return redirect("forms:builder", form_id=form_id)

    if request.method == "POST":
        form = QuestionOptionForm(request.POST)
        if form.is_valid():
            try:
                update_question_option(
                    option=option,
                    owner=request.user,
                    label=form.cleaned_data["label"],
                )
            except ValidationError as exc:
                _add_validation_errors(form, exc)
            else:
                messages.success(request, "Option updated.")
                return redirect("forms:builder", form_id=form_id)
    else:
        form = QuestionOptionForm(initial={"label": option.label})

    return render(
        request,
        "forms/builder/option_form.html",
        {
            "form": form,
            "managed_form": managed_form,
            "question": question,
            "option": option,
            "page_title": "Edit option",
            "submit_label": "Save option",
        },
    )


@login_required
@require_POST
def option_delete(request, form_id, question_id, option_id):
    option = _owned_option_or_404(
        owner=request.user,
        form_id=form_id,
        question_id=question_id,
        option_id=option_id,
    )
    try:
        delete_question_option(option=option, owner=request.user)
    except ValidationError as exc:
        messages.error(request, _first_validation_message(exc))
    else:
        messages.success(request, "Option deleted and ordering repaired.")
    return redirect("forms:builder", form_id=form_id)


@login_required
@require_POST
def option_move(request, form_id, question_id, option_id, direction):
    option = _owned_option_or_404(
        owner=request.user,
        form_id=form_id,
        question_id=question_id,
        option_id=option_id,
    )
    try:
        move_question_option(option=option, owner=request.user, direction=direction)
    except ValidationError as exc:
        messages.error(request, _first_validation_message(exc))
    return redirect("forms:builder", form_id=form_id)
