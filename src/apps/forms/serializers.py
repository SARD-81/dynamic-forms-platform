from rest_framework import serializers

from .models import Form, POSITIVE_INTEGER_MAX, Question, QuestionOption


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


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ("id", "label", "order")
        read_only_fields = fields


class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = (
            "id",
            "text",
            "question_type",
            "is_required",
            "order",
            "max_length",
            "min_value",
            "max_value",
            "created_at",
            "updated_at",
            "options",
        )
        read_only_fields = fields


class QuestionWriteSerializer(serializers.Serializer):
    text = serializers.CharField()
    question_type = serializers.ChoiceField(choices=Question.QuestionType.choices)
    is_required = serializers.BooleanField(required=False, default=False)
    max_length = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=POSITIVE_INTEGER_MAX,
    )
    min_value = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=18,
        decimal_places=6,
    )
    max_value = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=18,
        decimal_places=6,
    )


class QuestionReorderSerializer(serializers.Serializer):
    question_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
    )


class QuestionOptionWriteSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=255)


class QuestionOptionReorderSerializer(serializers.Serializer):
    option_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
    )
