from rest_framework import serializers

from apps.forms.participant_serializers import ParticipantSubmissionAnswerSerializer


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


class ParticipantStepRunSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    step_id = serializers.IntegerField(source="process_step_id")
    order = serializers.IntegerField(source="process_step.order")
    form_public_id = serializers.UUIDField(source="process_step.form.public_id")
    status = serializers.CharField()
    completed_at = serializers.DateTimeField(allow_null=True)


class ParticipantProcessRunDetailSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    status = serializers.CharField()
    started_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)
    resume_token = serializers.SerializerMethodField()
    steps = serializers.SerializerMethodField()

    def get_resume_token(self, obj):
        if isinstance(obj, dict):
            return obj.get("resume_token")
        return getattr(obj, "resume_token", None)

    def get_steps(self, obj):
        if isinstance(obj, dict):
            return obj.get("steps", [])
        step_runs = getattr(obj, "ordered_step_runs", None)
        if step_runs is None:
            step_runs = obj.step_runs.select_related("process_step__form").order_by(
                "process_step__order", "id"
            )
        return ParticipantStepRunSerializer(step_runs, many=True).data


class ParticipantCompleteStepInputSerializer(serializers.Serializer):
    answers = ParticipantSubmissionAnswerSerializer(many=True, allow_empty=True)
