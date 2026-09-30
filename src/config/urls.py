from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

handler403 = "apps.core.views.permission_denied"
handler404 = "apps.core.views.page_not_found"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("forms/", include("apps.forms.urls")),
    path("processes/", include("apps.processes.urls")),
    path("reports/", include("apps.reports.urls")),
    path("p/forms/", include("apps.forms.participant_urls")),
    path("p/processes/", include("apps.processes.participant_urls")),
    # API v1 Base Routing (Namespace برداشته شد)
    path("api/v1/", include("config.api_router")),
    # OpenAPI Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Core Root URLs
    path("", include("apps.core.urls")),
]
