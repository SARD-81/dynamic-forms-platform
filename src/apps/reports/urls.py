from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.subscription_list, name="list"),
    path("new/", views.subscription_create, name="create"),
    path("preview/", views.report_preview, name="preview"),
    path("<int:subscription_id>/edit/", views.subscription_update, name="update"),
    path(
        "<int:subscription_id>/deactivate/",
        views.subscription_deactivate,
        name="deactivate",
    ),
]
