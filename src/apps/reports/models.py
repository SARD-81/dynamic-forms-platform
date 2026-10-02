from django.conf import settings
from django.db import models


class ReportSubscription(models.Model):
    class Frequency(models.TextChoices):
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"

    class DeliveryMethod(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        API = "API", "API"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="report_subscriptions",
    )
    frequency = models.CharField(
        max_length=10,
        choices=Frequency.choices,
    )
    delivery_method = models.CharField(
        max_length=10,
        choices=DeliveryMethod.choices,
    )
    email = models.EmailField(null=True, blank=True)
    endpoint_url = models.URLField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["is_active", "frequency"],
                name="report_active_freq_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        delivery_method="EMAIL",
                        email__isnull=False,
                        endpoint_url__isnull=True,
                    )
                    | models.Q(
                        delivery_method="API",
                        email__isnull=True,
                        endpoint_url__isnull=False,
                    )
                ),
                name="report_delivery_target_ck",
            ),
        ]
