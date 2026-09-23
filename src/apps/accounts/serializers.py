from django.conf import settings
from rest_framework import serializers

from .models import User


class RegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(
        regex=rf"^\d{{{settings.ACCOUNT_OTP_LENGTH}}}$",
        max_length=settings.ACCOUNT_OTP_LENGTH,
        min_length=settings.ACCOUNT_OTP_LENGTH,
    )


class OTPResendSerializer(serializers.Serializer):
    email = serializers.EmailField()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class CurrentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")
        read_only_fields = fields
