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
    path(
        "<uuid:public_id>/runs/start/",
        participant_views.participant_process_run_start,
        name="run_start",
    ),
    path(
        "<uuid:public_id>/runs/resume/",
        participant_views.participant_process_resume,
        name="resume",
    ),
    path(
        "<uuid:public_id>/runs/<uuid:run_public_id>/",
        participant_views.participant_process_run_detail,
        name="run_detail",
    ),
    path(
        "<uuid:public_id>/runs/<uuid:run_public_id>/steps/<int:step_id>/",
        participant_views.participant_process_step,
        name="step",
    ),
]
