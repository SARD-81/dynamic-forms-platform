from django.apps import apps


def form_has_active_process_runs(*, form_id):
    """Cross-domain check used before closing a published form."""
    ProcessRun = apps.get_model("processes", "ProcessRun")

    return ProcessRun.objects.filter(
        process__steps__form_id=form_id,
        status=ProcessRun.Status.IN_PROGRESS,
    ).exists()
