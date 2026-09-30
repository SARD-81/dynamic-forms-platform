from django.urls import path

from .api_views import (
    PeriodicReportPreviewAPIView,
    ReportSubscriptionDeactivateAPIView,
    ReportSubscriptionDetailAPIView,
    ReportSubscriptionListCreateAPIView,
)

urlpatterns = [
    path("subscriptions/", ReportSubscriptionListCreateAPIView.as_view(), name="report_subscription_list"),
    path(
        "subscriptions/<int:subscription_id>/",
        ReportSubscriptionDetailAPIView.as_view(),
        name="report_subscription_detail",
    ),
    path(
        "subscriptions/<int:subscription_id>/deactivate/",
        ReportSubscriptionDeactivateAPIView.as_view(),
        name="report_subscription_deactivate",
    ),
    path("preview/", PeriodicReportPreviewAPIView.as_view(), name="periodic_report_preview"),
]
