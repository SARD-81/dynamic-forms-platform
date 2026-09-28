from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render

from .forms import CategoryForm
from .selectors import get_category_choices_for_owner, get_category_for_owner
from .services import create_category, delete_category, rename_category


def home(request):
    return render(request, "home.html")


@login_required
def dashboard(request):
    return render(request, "dashboard/index.html")


def _add_category_validation_errors(form, exc):
    if hasattr(exc, "message_dict"):
        errors = exc.message_dict
    else:
        errors = {"__all__": exc.messages}

    for field, messages_list in errors.items():
        target = field if field in form.fields else None
        for message in messages_list:
            form.add_error(target, message)


def _owned_category_or_404(*, user, category_id):
    category = get_category_for_owner(owner=user, category_id=category_id)
    if category is None:
        raise Http404
    return category


@login_required
def category_list(request):
    categories = get_category_choices_for_owner(owner=request.user)
    return render(request, "categories/list.html", {"categories": categories})


@login_required
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            try:
                create_category(
                    owner=request.user,
                    name=form.cleaned_data["name"],
                )
            except ValidationError as exc:
                _add_category_validation_errors(form, exc)
            else:
                messages.success(request, "Category created.")
                return redirect("core:category_list")
    else:
        form = CategoryForm()

    return render(
        request,
        "categories/form.html",
        {
            "form": form,
            "page_title": "Create category",
            "submit_label": "Create category",
        },
    )


@login_required
def category_update(request, category_id):
    category = _owned_category_or_404(user=request.user, category_id=category_id)

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            try:
                rename_category(
                    category=category,
                    owner=request.user,
                    name=form.cleaned_data["name"],
                )
            except ValidationError as exc:
                _add_category_validation_errors(form, exc)
            else:
                messages.success(request, "Category renamed.")
                return redirect("core:category_list")
    else:
        form = CategoryForm(initial={"name": category.name})

    return render(
        request,
        "categories/form.html",
        {
            "form": form,
            "category": category,
            "page_title": "Rename category",
            "submit_label": "Save changes",
        },
    )


@login_required
def category_delete(request, category_id):
    category = _owned_category_or_404(user=request.user, category_id=category_id)

    if request.method == "POST":
        delete_category(category=category, owner=request.user)
        messages.success(request, "Category deleted. Related forms and processes were kept.")
        return redirect("core:category_list")

    return render(
        request,
        "categories/confirm_delete.html",
        {"category": category},
    )


def permission_denied(request, exception):
    return render(request, "403.html", status=403)


def page_not_found(request, exception):
    return render(request, "404.html", status=404)
