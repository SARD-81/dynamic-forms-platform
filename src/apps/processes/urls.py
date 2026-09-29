from django.urls import path

from . import views

app_name = "processes"

urlpatterns = [
    path("", views.process_list, name="list"),
    path("new/", views.process_create, name="create"),
    path("<int:process_id>/", views.process_detail, name="detail"),
    path("<int:process_id>/edit/", views.process_update, name="update"),
    path("<int:process_id>/publish/", views.process_publish, name="publish"),
    path("<int:process_id>/close/", views.process_close, name="close"),
    path("<int:process_id>/delete/", views.process_delete, name="delete"),
    path("<int:process_id>/builder/", views.process_builder, name="builder"),
    path(
        "<int:process_id>/builder/steps/new/",
        views.process_step_create,
        name="step_create",
    ),
    path(
        "<int:process_id>/builder/steps/<int:step_id>/delete/",
        views.process_step_delete,
        name="step_delete",
    ),
    path(
        "<int:process_id>/builder/steps/<int:step_id>/move/<str:direction>/",
        views.process_step_move,
        name="step_move",
    ),
]
