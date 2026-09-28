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
]
