from rest_framework import serializers


class ParticipantOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    order = serializers.IntegerField()


class ParticipantQuestionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    text = serializers.CharField()
    question_type = serializers.CharField()
    is_required = serializers.BooleanField()
    order = serializers.IntegerField()
    max_length = serializers.IntegerField(allow_null=True)
    min_value = serializers.DecimalField(
        max_digits=18,
        decimal_places=6,
        allow_null=True,
    )
    max_value = serializers.DecimalField(
        max_digits=18,
        decimal_places=6,
        allow_null=True,
    )
    options = ParticipantOptionSerializer(many=True)


class ParticipantFormSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    visibility = serializers.CharField()
    status = serializers.CharField()
    questions = ParticipantQuestionSerializer(many=True)


class ParticipantUnlockSerializer(serializers.Serializer):
    password = serializers.CharField(trim_whitespace=False, write_only=True)
