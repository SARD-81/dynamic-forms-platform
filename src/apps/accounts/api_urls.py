from django.urls import path

from .api_views import (
    CSRFApiView,
    CurrentUserAPIView,
    LoginAPIView,
    LogoutAPIView,
    RegisterAPIView,
    ResendOTPAPIView,
    VerifyOTPAPIView,
)

app_name = "accounts_api"

urlpatterns = [
    path("csrf/", CSRFApiView.as_view(), name="csrf"),
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("verify/", VerifyOTPAPIView.as_view(), name="verify"),
    path("resend/", ResendOTPAPIView.as_view(), name="resend"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("me/", CurrentUserAPIView.as_view(), name="me"),
]
