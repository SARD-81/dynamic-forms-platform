from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import (
    AccountServiceError,
    AccountValidationError,
    OTPEmailDeliveryError,
    OTPThrottleError,
)
from .serializers import (
    CurrentUserSerializer,
    LoginSerializer,
    OTPResendSerializer,
    OTPVerificationSerializer,
    RegistrationSerializer,
)
from .services import (
    login_user,
    logout_user,
    register_user,
    resend_registration_otp,
    verify_registration_otp,
)


def _error_response(exc):
    if isinstance(exc, AccountValidationError):
        return Response(
            {
                "detail": exc.public_message,
                "errors": exc.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, OTPThrottleError):
        return Response(
            {
                "detail": str(exc),
                "retry_after": exc.retry_after,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(exc.retry_after)},
        )

    if isinstance(exc, OTPEmailDeliveryError):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {"detail": str(exc)},
        status=status.HTTP_400_BAD_REQUEST,
    )


class CSRFApiView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class RegisterAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = register_user(**serializer.validated_data)
        except AccountServiceError as exc:
            response = _error_response(exc)
            if isinstance(exc, OTPEmailDeliveryError):
                response.data["account_created"] = True
                response.data["email"] = serializer.validated_data["email"]
            return response

        return Response(
            {
                "detail": "Account created. Check your email for the verification code.",
                "user": CurrentUserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_protect, name="dispatch")
class VerifyOTPAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = verify_registration_otp(**serializer.validated_data)
        except AccountServiceError as exc:
            return _error_response(exc)

        return Response(
            {
                "detail": "Email verified. You can now sign in.",
                "user": CurrentUserSerializer(user).data,
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class ResendOTPAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            resend_registration_otp(**serializer.validated_data)
        except AccountServiceError as exc:
            return _error_response(exc)

        return Response(
            {"detail": "A new verification code was sent."},
        )


@method_decorator(csrf_protect, name="dispatch")
class LoginAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = login_user(request, **serializer.validated_data)
        except AccountServiceError as exc:
            return _error_response(exc)

        return Response(
            {
                "detail": "Signed in.",
                "user": CurrentUserSerializer(user).data,
            }
        )


class LogoutAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout_user(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CurrentUserSerializer(request.user).data)
