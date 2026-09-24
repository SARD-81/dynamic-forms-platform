from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

handler403 = "apps.core.views.permission_denied"
handler404 = "apps.core.views.page_not_found"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),

    # API v1 Base Routing
    path("api/v1/", include("config.api_router", namespace="api_v1")),

    # OpenAPI Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Core Root URLs
    path("", include("apps.core.urls")),
]