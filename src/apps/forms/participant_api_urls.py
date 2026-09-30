from django.urls import path

from .participant_api_views import (
    ParticipantFormDetailAPIView,
    ParticipantFormSubmissionAPIView,
    ParticipantFormUnlockAPIView,
)

app_name = "forms_participant_api"

urlpatterns = [
    path("<uuid:public_id>/", ParticipantFormDetailAPIView.as_view(), name="detail"),
    path(
        "<uuid:public_id>/submissions/",
        ParticipantFormSubmissionAPIView.as_view(),
        name="submission",
    ),
    path("<uuid:public_id>/unlock/", ParticipantFormUnlockAPIView.as_view(), name="unlock"),
]
