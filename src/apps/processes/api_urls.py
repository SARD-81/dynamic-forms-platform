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

app_name = "processes_api"

urlpatterns = [
    path("", ProcessListCreateAPIView.as_view(), name="process-list"),
    path("<int:process_id>/", ProcessDetailAPIView.as_view(), name="process-detail"),
    path("<int:process_id>/publish/", ProcessPublishAPIView.as_view(), name="process-publish"),
    path("<int:process_id>/close/", ProcessCloseAPIView.as_view(), name="process-close"),
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
