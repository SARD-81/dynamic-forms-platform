from rest_framework import serializers


class ParticipantProcessStepSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    order = serializers.IntegerField()
    form_public_id = serializers.UUIDField()


class ParticipantProcessSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    process_type = serializers.CharField()
    visibility = serializers.CharField()
    status = serializers.CharField()
    steps = ParticipantProcessStepSerializer(many=True)


class ParticipantUnlockSerializer(serializers.Serializer):
    password = serializers.CharField(trim_whitespace=False, write_only=True)
