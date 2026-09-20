from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Project user model. Created before the first project migration."""

    email = models.EmailField(unique=True)


class OTPChallenge(models.Model):
    class Purpose(models.TextChoices):
        REGISTER = "REGISTER", "Register"
        LOGIN = "LOGIN", "Login"

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="otp_challenges",
    )
    purpose = models.CharField(max_length=16, choices=Purpose.choices)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempt_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["user", "purpose", "-created_at"],
                name="otp_user_purpose_created_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(attempt_count__gte=0),
                name="otp_attempt_count_gte_0_ck",
            ),
        ]
