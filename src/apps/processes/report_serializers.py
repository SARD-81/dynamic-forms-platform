from rest_framework import serializers


class ProcessReportRecentRunSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    status = serializers.CharField()
    started_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)
    respondent_type = serializers.ChoiceField(choices=("anonymous", "authenticated"))


class ProcessReportStepSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    order = serializers.IntegerField()
    form_id = serializers.IntegerField()
    form_public_id = serializers.UUIDField()
    form_title = serializers.CharField()
    completed_count = serializers.IntegerField()
    available_count = serializers.IntegerField()
    locked_count = serializers.IntegerField()


class ProcessReportSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    public_id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.CharField()
    process_type = serializers.CharField()
    visibility = serializers.CharField()
    view_count = serializers.IntegerField()
    total_runs = serializers.IntegerField()
    completed_runs = serializers.IntegerField()
    in_progress_runs = serializers.IntegerField()
    response_count = serializers.IntegerField()
    completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    completion_semantic = serializers.CharField()
    recent_activity = ProcessReportRecentRunSerializer(many=True)
    steps = ProcessReportStepSummarySerializer(many=True)


class ProcessReportRunListSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    status = serializers.CharField()
    respondent_type = serializers.ChoiceField(choices=("anonymous", "authenticated"))
    started_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)
    completed_steps = serializers.IntegerField()
    total_steps = serializers.IntegerField()


class ProcessReportSubmissionReferenceSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    submitted_at = serializers.DateTimeField()
    respondent_type = serializers.ChoiceField(choices=("anonymous", "authenticated"))


class ProcessReportRunStepSerializer(serializers.Serializer):
    step_id = serializers.IntegerField()
    order = serializers.IntegerField()
    status = serializers.CharField()
    completed_at = serializers.DateTimeField(allow_null=True)
    form_id = serializers.IntegerField()
    form_public_id = serializers.UUIDField()
    form_title = serializers.CharField()
    submission = ProcessReportSubmissionReferenceSerializer(allow_null=True)


class ProcessReportRunDetailSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    status = serializers.CharField()
    respondent_type = serializers.ChoiceField(choices=("anonymous", "authenticated"))
    started_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)
    steps = ProcessReportRunStepSerializer(many=True)
