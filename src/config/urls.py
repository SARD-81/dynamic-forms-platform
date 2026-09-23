from django.contrib import admin
from django.urls import include, path

handler403 = "apps.core.views.permission_denied"
handler404 = "apps.core.views.page_not_found"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
]
