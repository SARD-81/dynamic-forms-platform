from rest_framework import serializers

from .models import ReportSubscription


class ReportSubscriptionSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.get_username", read_only=True)

    class Meta:
        model = ReportSubscription
        fields = [
            "id",
            "created_by",
            "frequency",
            "delivery_method",
            "email",
            "endpoint_url",
            "is_active",
            "last_sent_at",
            "created_at",
            "updated_at",
        ]


class ReportSubscriptionWriteSerializer(serializers.Serializer):
    frequency = serializers.ChoiceField(choices=ReportSubscription.Frequency.choices)
    delivery_method = serializers.ChoiceField(choices=ReportSubscription.DeliveryMethod.choices)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    endpoint_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        method = attrs.get("delivery_method")
        email = attrs.get("email") or None
        endpoint_url = attrs.get("endpoint_url") or None
        if method == ReportSubscription.DeliveryMethod.EMAIL:
            if not email:
                raise serializers.ValidationError({"email": "Required for EMAIL delivery."})
            if endpoint_url:
                raise serializers.ValidationError(
                    {"endpoint_url": "Must be empty for EMAIL delivery."}
                )
        elif method == ReportSubscription.DeliveryMethod.API:
            if not endpoint_url:
                raise serializers.ValidationError({"endpoint_url": "Required for API delivery."})
            if email:
                raise serializers.ValidationError({"email": "Must be empty for API delivery."})
        return attrs


class CurrentStatusSerializer(serializers.Serializer):
    draft = serializers.IntegerField()
    published = serializers.IntegerField()
    closed = serializers.IntegerField()


class FormActivitySerializer(serializers.Serializer):
    created = serializers.IntegerField()
    created_current_status = CurrentStatusSerializer()
    submissions = serializers.IntegerField()


class ProcessActivitySerializer(serializers.Serializer):
    created = serializers.IntegerField()
    created_current_status = CurrentStatusSerializer()
    runs_started = serializers.IntegerField()
    runs_completed = serializers.IntegerField()


class CumulativeViewsSerializer(serializers.Serializer):
    forms = serializers.IntegerField()
    processes = serializers.IntegerField()


class ReportActivitySerializer(serializers.Serializer):
    forms = FormActivitySerializer()
    processes = ProcessActivitySerializer()
    cumulative_views = CumulativeViewsSerializer()


class PeriodicReportPayloadSerializer(serializers.Serializer):
    schema_version = serializers.CharField()
    frequency = serializers.ChoiceField(choices=ReportSubscription.Frequency.choices)
    period_start = serializers.DateTimeField()
    period_end = serializers.DateTimeField()
    generated_at = serializers.DateTimeField()
    activity = ReportActivitySerializer()
