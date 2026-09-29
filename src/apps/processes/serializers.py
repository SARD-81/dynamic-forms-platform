from rest_framework import serializers

from apps.forms.models import Form

from .models import Process, ProcessStep


class ProcessStepFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = Form
        fields = ("id", "public_id", "title", "status")
        read_only_fields = fields


class ProcessStepSerializer(serializers.ModelSerializer):
    form = ProcessStepFormSerializer(read_only=True)
    form_id = serializers.IntegerField(source="form.id", read_only=True)
    form_public_id = serializers.UUIDField(source="form.public_id", read_only=True)
    form_title = serializers.CharField(source="form.title", read_only=True)
    form_status = serializers.CharField(source="form.status", read_only=True)

    class Meta:
        model = ProcessStep
        fields = (
            "id",
            "order",
            "form_id",
            "form_public_id",
            "form_title",
            "form_status",
            "form",
        )
        read_only_fields = fields


class ProcessSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(read_only=True, allow_null=True)
    steps = ProcessStepSerializer(many=True, read_only=True)

    class Meta:
        model = Process
        fields = (
            "id",
            "public_id",
            "title",
            "description",
            "category_id",
            "process_type",
            "visibility",
            "status",
            "view_count",
            "created_at",
            "updated_at",
            "steps",
        )
        read_only_fields = fields


class ProcessWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    category_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    process_type = serializers.ChoiceField(choices=Process.ProcessType.choices)
    visibility = serializers.ChoiceField(
        choices=Process.Visibility.choices,
        required=False,
        default=Process.Visibility.PUBLIC,
    )
    access_password = serializers.CharField(
        required=False,
        allow_blank=False,
        trim_whitespace=False,
        write_only=True,
    )


class ProcessUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    category_id = serializers.IntegerField(required=False, allow_null=True)
    process_type = serializers.ChoiceField(choices=Process.ProcessType.choices, required=False)
    visibility = serializers.ChoiceField(choices=Process.Visibility.choices, required=False)
    access_password = serializers.CharField(
        required=False,
        allow_blank=False,
        trim_whitespace=False,
        write_only=True,
    )


class ProcessStepWriteSerializer(serializers.Serializer):
    form_id = serializers.IntegerField(min_value=1)


class ProcessStepReorderSerializer(serializers.Serializer):
    step_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
    )
