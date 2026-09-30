from django.urls import include, path

from apps.core.api_views import api_root

urlpatterns = [
    path("", api_root, name="api_v1_root"),
    path("accounts/", include("apps.accounts.api_urls")),
    path("categories/", include("apps.core.api_urls")),
    path("forms/", include("apps.forms.api_urls")),
    path("processes/", include("apps.processes.api_urls")),
    path("reports/", include("apps.reports.api_urls")),
    path("public/forms/", include("apps.forms.participant_api_urls")),
    path("public/processes/", include("apps.processes.participant_api_urls")),
]
