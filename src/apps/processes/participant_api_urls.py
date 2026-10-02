from django.urls import path

from .participant_api_views import (
    ParticipantProcessDetailAPIView,
    ParticipantProcessRunDetailAPIView,
    ParticipantProcessRunStartAPIView,
    ParticipantProcessStepCompleteAPIView,
    ParticipantProcessUnlockAPIView,
)

app_name = "processes_participant_api"

urlpatterns = [
    path("<uuid:public_id>/", ParticipantProcessDetailAPIView.as_view(), name="detail"),
    path(
        "<uuid:public_id>/unlock/",
        ParticipantProcessUnlockAPIView.as_view(),
        name="unlock",
    ),
    path(
        "<uuid:public_id>/runs/",
        ParticipantProcessRunStartAPIView.as_view(),
        name="run-start",
    ),
    path(
        "<uuid:public_id>/runs/<uuid:run_public_id>/",
        ParticipantProcessRunDetailAPIView.as_view(),
        name="run-detail",
    ),
    path(
        "<uuid:public_id>/runs/<uuid:run_public_id>/steps/<int:step_id>/complete/",
        ParticipantProcessStepCompleteAPIView.as_view(),
        name="step-complete",
    ),
]
