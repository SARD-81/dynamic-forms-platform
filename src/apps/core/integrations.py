from django.apps import apps


def form_has_active_process_runs(*, form_id):
    """Cross-domain check used while the Form row is locked for closure."""
    ProcessRun = apps.get_model("processes", "ProcessRun")

    return ProcessRun.objects.filter(
        process__steps__form_id=form_id,
        status=ProcessRun.Status.IN_PROGRESS,
    ).exists()


def lock_required_forms_for_process_run(*, process_id):
    """Lock required Form rows before a ProcessRun validates and starts.

    Call this inside the same transaction that validates Form availability and
    creates the ProcessRun. Form closure locks the same rows, so the two flows
    cannot race past each other's lifecycle checks.
    """
    Form = apps.get_model("forms", "Form")
    ProcessStep = apps.get_model("processes", "ProcessStep")

    form_ids = (
        ProcessStep.objects.filter(process_id=process_id)
        .order_by("form_id")
        .values_list("form_id", flat=True)
    )
    return list(Form.objects.select_for_update().filter(pk__in=form_ids).order_by("pk"))
