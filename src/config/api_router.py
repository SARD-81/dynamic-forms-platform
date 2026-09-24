from django.urls import include, path

urlpatterns = [
    path("accounts/", include("apps.accounts.api_urls")),
]
