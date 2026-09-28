from django.urls import path

from .api_views import (
    FormCloseAPIView,
    FormDetailAPIView,
    FormListCreateAPIView,
    FormPublishAPIView,
)

app_name = "forms_api"

urlpatterns = [
    path("", FormListCreateAPIView.as_view(), name="form-list"),
    path("<int:form_id>/", FormDetailAPIView.as_view(), name="form-detail"),
    path("<int:form_id>/publish/", FormPublishAPIView.as_view(), name="form-publish"),
    path("<int:form_id>/close/", FormCloseAPIView.as_view(), name="form-close"),
]
