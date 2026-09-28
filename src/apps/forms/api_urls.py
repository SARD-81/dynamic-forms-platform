from django.urls import path

from .api_views import (
    FormCloseAPIView,
    FormDetailAPIView,
    FormListCreateAPIView,
    FormPublishAPIView,
    QuestionDetailAPIView,
    QuestionListCreateAPIView,
    QuestionOptionDetailAPIView,
    QuestionOptionListCreateAPIView,
    QuestionOptionReorderAPIView,
    QuestionReorderAPIView,
)

app_name = "forms_api"

urlpatterns = [
    path("", FormListCreateAPIView.as_view(), name="form-list"),
    path("<int:form_id>/", FormDetailAPIView.as_view(), name="form-detail"),
    path("<int:form_id>/publish/", FormPublishAPIView.as_view(), name="form-publish"),
    path("<int:form_id>/close/", FormCloseAPIView.as_view(), name="form-close"),
    path(
        "<int:form_id>/questions/",
        QuestionListCreateAPIView.as_view(),
        name="question-list",
    ),
    path(
        "<int:form_id>/questions/reorder/",
        QuestionReorderAPIView.as_view(),
        name="question-reorder",
    ),
    path(
        "<int:form_id>/questions/<int:question_id>/",
        QuestionDetailAPIView.as_view(),
        name="question-detail",
    ),
    path(
        "<int:form_id>/questions/<int:question_id>/options/",
        QuestionOptionListCreateAPIView.as_view(),
        name="option-list",
    ),
    path(
        "<int:form_id>/questions/<int:question_id>/options/reorder/",
        QuestionOptionReorderAPIView.as_view(),
        name="option-reorder",
    ),
    path(
        "<int:form_id>/questions/<int:question_id>/options/<int:option_id>/",
        QuestionOptionDetailAPIView.as_view(),
        name="option-detail",
    ),
]
