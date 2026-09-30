from django.urls import path

from .api_views import (
    ProcessCloseAPIView,
    ProcessDetailAPIView,
    ProcessListCreateAPIView,
    ProcessPublishAPIView,
    ProcessStepDetailAPIView,
    ProcessStepListCreateAPIView,
    ProcessStepReorderAPIView,
)
from .report_api_views import (
    ProcessReportRunDetailAPIView,
    ProcessReportRunListAPIView,
    ProcessReportSummaryAPIView,
)

app_name = "processes_api"

urlpatterns = [
    path("", ProcessListCreateAPIView.as_view(), name="process-list"),
    path("<int:process_id>/", ProcessDetailAPIView.as_view(), name="process-detail"),
    path("<int:process_id>/publish/", ProcessPublishAPIView.as_view(), name="process-publish"),
    path("<int:process_id>/close/", ProcessCloseAPIView.as_view(), name="process-close"),
    path(
        "<int:process_id>/report/",
        ProcessReportSummaryAPIView.as_view(),
        name="process-report",
    ),
    path(
        "<int:process_id>/runs/",
        ProcessReportRunListAPIView.as_view(),
        name="process-runs",
    ),
    path(
        "<int:process_id>/runs/<uuid:run_public_id>/",
        ProcessReportRunDetailAPIView.as_view(),
        name="process-run-detail",
    ),
    path("<int:process_id>/steps/", ProcessStepListCreateAPIView.as_view(), name="step-list"),
    path(
        "<int:process_id>/steps/reorder/",
        ProcessStepReorderAPIView.as_view(),
        name="step-reorder",
    ),
    path(
        "<int:process_id>/steps/<int:step_id>/",
        ProcessStepDetailAPIView.as_view(),
        name="step-detail",
    ),
]
