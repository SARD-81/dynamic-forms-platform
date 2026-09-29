from django.urls import path

from .participant_api_views import (
    ParticipantProcessDetailAPIView,
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
]
