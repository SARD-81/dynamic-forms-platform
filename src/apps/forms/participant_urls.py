from django.urls import path

from . import participant_views

app_name = "forms_participant"

urlpatterns = [
    path("<uuid:public_id>/", participant_views.participant_form_detail, name="detail"),
    path(
        "<uuid:public_id>/submit/",
        participant_views.participant_form_submit,
        name="submit",
    ),
    path("<uuid:public_id>/unlock/", participant_views.participant_form_unlock, name="unlock"),
]
