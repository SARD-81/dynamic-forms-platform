from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render

from .report_selectors import (
    PROCESS_REPORT_PAGE_SIZE,
    get_process_report_run_detail,
    get_process_report_runs,
    get_process_report_summary,
    process_run_list_item,
)


@login_required
def process_report_dashboard(request, process_id):
    summary = get_process_report_summary(owner=request.user, process_id=process_id)
    if summary is None:
        raise Http404
    return render(
        request,
        "processes/reports/dashboard.html",
        {"report": summary},
    )


@login_required
def process_report_runs(request, process_id):
    summary = get_process_report_summary(owner=request.user, process_id=process_id)
    if summary is None:
        raise Http404

    queryset = get_process_report_runs(owner=request.user, process_id=process_id)
    paginator = Paginator(queryset, PROCESS_REPORT_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    run_items = [process_run_list_item(item) for item in page_obj.object_list]

    return render(
        request,
        "processes/reports/runs.html",
        {
            "report": summary,
            "page_obj": page_obj,
            "run_items": run_items,
        },
    )


@login_required
def process_report_run_detail(request, process_id, run_public_id):
    summary = get_process_report_summary(owner=request.user, process_id=process_id)
    if summary is None:
        raise Http404

    run = get_process_report_run_detail(
        owner=request.user,
        process_id=process_id,
        run_public_id=run_public_id,
    )
    if run is None:
        raise Http404

    return render(
        request,
        "processes/reports/run_detail.html",
        {
            "report": summary,
            "run": run,
        },
    )
