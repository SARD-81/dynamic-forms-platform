from rest_framework import serializers


class FormReportOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    order = serializers.IntegerField()
    count = serializers.IntegerField()
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class FormReportQuestionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    text = serializers.CharField()
    question_type = serializers.CharField()
    is_required = serializers.BooleanField()
    order = serializers.IntegerField()
    answered_count = serializers.IntegerField()
    unanswered_count = serializers.IntegerField()
    percentage_denominator = serializers.CharField()
    percentage_denominator_count = serializers.IntegerField()
    checkbox_percentage_note = serializers.CharField(allow_blank=True)
    number_min = serializers.DecimalField(
        max_digits=30,
        decimal_places=6,
        allow_null=True,
    )
    number_max = serializers.DecimalField(
        max_digits=30,
        decimal_places=6,
        allow_null=True,
    )
    number_sum = serializers.DecimalField(
        max_digits=30,
        decimal_places=6,
        allow_null=True,
    )
    number_average = serializers.DecimalField(
        max_digits=30,
        decimal_places=6,
        allow_null=True,
    )
    options = FormReportOptionSerializer(many=True)


class FormReportRecentActivitySerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    submitted_at = serializers.DateTimeField()
    respondent_type = serializers.ChoiceField(choices=("anonymous", "authenticated"))


class FormReportTimelineSerializer(serializers.Serializer):
    date = serializers.DateField()
    count = serializers.IntegerField()


class FormReportSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    public_id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.CharField()
    view_count = serializers.IntegerField()
    total_submissions = serializers.IntegerField()
    recent_activity = FormReportRecentActivitySerializer(many=True)
    timeline = FormReportTimelineSerializer(many=True)
    questions = FormReportQuestionSerializer(many=True)


class FormReportSubmissionListSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    submitted_at = serializers.DateTimeField()
    respondent_type = serializers.ChoiceField(choices=("anonymous", "authenticated"))


class FormReportSelectedOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    order = serializers.IntegerField()


class FormReportAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    question_text = serializers.CharField()
    question_type = serializers.CharField()
    question_order = serializers.IntegerField()
    text_value = serializers.CharField(allow_null=True, allow_blank=True)
    number_value = serializers.DecimalField(
        max_digits=18,
        decimal_places=6,
        allow_null=True,
    )
    selected_options = FormReportSelectedOptionSerializer(many=True)


class FormReportSubmissionDetailSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    submitted_at = serializers.DateTimeField()
    respondent_type = serializers.ChoiceField(choices=("anonymous", "authenticated"))
    answers = FormReportAnswerSerializer(many=True)
