from rest_framework import serializers

from .models import ReportSubscription
from .services import _clean_and_validate_subscription_targets, _validate_frequency


class ReportSubscriptionSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = ReportSubscription
        fields = [
            "id",
            "frequency",
            "delivery_method",
            "email",
            "endpoint_url",
            "is_active",
            "last_sent_at",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "last_sent_at",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        frequency = attrs.get("frequency", instance.frequency if instance else None)
        delivery_method = attrs.get(
            "delivery_method", instance.delivery_method if instance else None
        )
        email = attrs.get("email", instance.email if instance else None)
        endpoint_url = attrs.get("endpoint_url", instance.endpoint_url if instance else None)

        try:
            if frequency is not None:
                _validate_frequency(frequency)
            if delivery_method is not None:
                cleaned_email, cleaned_url = _clean_and_validate_subscription_targets(
                    delivery_method=delivery_method,
                    email=email,
                    endpoint_url=endpoint_url,
                )
                attrs["email"] = cleaned_email
                attrs["endpoint_url"] = cleaned_url
        except serializers.ValidationError:
            raise
        except Exception as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict) from exc
            raise serializers.ValidationError(str(exc)) from exc

        return attrs
