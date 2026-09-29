from django.urls import path

from . import participant_views

app_name = "processes_participant"

urlpatterns = [
    path("<uuid:public_id>/", participant_views.participant_process_detail, name="detail"),
    path(
        "<uuid:public_id>/unlock/",
        participant_views.participant_process_unlock,
        name="unlock",
    ),
]
