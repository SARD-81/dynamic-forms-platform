from rest_framework import serializers

from .models import Form


class FormSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Form
        fields = (
            "id",
            "public_id",
            "title",
            "description",
            "category_id",
            "visibility",
            "status",
            "view_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class FormWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    category_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    visibility = serializers.ChoiceField(
        choices=Form.Visibility.choices,
        required=False,
        default=Form.Visibility.PUBLIC,
    )
    access_password = serializers.CharField(
        required=False,
        allow_blank=False,
        trim_whitespace=False,
        write_only=True,
    )
