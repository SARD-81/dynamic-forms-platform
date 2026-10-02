from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("verify/", views.verify_view, name="verify"),
    path("otp/resend/", views.resend_view, name="resend"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("me/", views.current_user_view, name="me"),
]
