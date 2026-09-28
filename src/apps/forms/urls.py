from django.urls import path

from . import views

app_name = "forms"

urlpatterns = [
    path("", views.form_list, name="list"),
    path("new/", views.form_create, name="create"),
    path("<int:form_id>/", views.form_detail, name="detail"),
    path("<int:form_id>/edit/", views.form_update, name="update"),
    path("<int:form_id>/publish/", views.form_publish, name="publish"),
    path("<int:form_id>/close/", views.form_close, name="close"),
    path("<int:form_id>/delete/", views.form_delete, name="delete"),
    path("<int:form_id>/builder/", views.form_builder, name="builder"),
    path(
        "<int:form_id>/builder/questions/new/",
        views.question_create,
        name="question_create",
    ),
    path(
        "<int:form_id>/builder/questions/<int:question_id>/edit/",
        views.question_update,
        name="question_update",
    ),
    path(
        "<int:form_id>/builder/questions/<int:question_id>/delete/",
        views.question_delete,
        name="question_delete",
    ),
    path(
        "<int:form_id>/builder/questions/<int:question_id>/move/<str:direction>/",
        views.question_move,
        name="question_move",
    ),
    path(
        "<int:form_id>/builder/questions/<int:question_id>/options/new/",
        views.option_create,
        name="option_create",
    ),
    path(
        "<int:form_id>/builder/questions/<int:question_id>/options/<int:option_id>/edit/",
        views.option_update,
        name="option_update",
    ),
    path(
        "<int:form_id>/builder/questions/<int:question_id>/options/<int:option_id>/delete/",
        views.option_delete,
        name="option_delete",
    ),
    path(
        "<int:form_id>/builder/questions/<int:question_id>/options/<int:option_id>/move/<str:direction>/",
        views.option_move,
        name="option_move",
    ),
]
