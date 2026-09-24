from django.urls import path, include

app_name = "api_v1"

urlpatterns = [
    # اتصال Accounts API فعلی به روتر مشترک
    path("accounts/", include("apps.accounts.api_urls")),
]