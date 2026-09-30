from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render

from .report_selectors import (
    FORM_REPORT_PAGE_SIZE,
    get_form_report_submission_detail,
    get_form_report_submissions,
    get_form_report_summary,
    submission_list_item,
)


@login_required
def form_report_dashboard(request, form_id):
    summary = get_form_report_summary(owner=request.user, form_id=form_id)
    if summary is None:
        raise Http404
    return render(
        request,
        "forms/reports/dashboard.html",
        {"report": summary},
    )


@login_required
def form_report_responses(request, form_id):
    summary = get_form_report_summary(owner=request.user, form_id=form_id)
    if summary is None:
        raise Http404

    queryset = get_form_report_submissions(
        owner=request.user,
        form_id=form_id,
    )
    paginator = Paginator(queryset, FORM_REPORT_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    response_items = [submission_list_item(item) for item in page_obj.object_list]

    return render(
        request,
        "forms/reports/responses.html",
        {
            "report": summary,
            "page_obj": page_obj,
            "response_items": response_items,
        },
    )


@login_required
def form_report_response_detail(request, form_id, submission_public_id):
    summary = get_form_report_summary(owner=request.user, form_id=form_id)
    if summary is None:
        raise Http404

    submission = get_form_report_submission_detail(
        owner=request.user,
        form_id=form_id,
        submission_public_id=submission_public_id,
    )
    if submission is None:
        raise Http404

    return render(
        request,
        "forms/reports/response_detail.html",
        {
            "report": summary,
            "submission": submission,
        },
    )
