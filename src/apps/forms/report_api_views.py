from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .report_selectors import (
    get_form_report_submission_detail,
    get_form_report_submissions,
    get_form_report_summary,
    submission_list_item,
)
from .report_serializers import (
    FormReportSubmissionDetailSerializer,
    FormReportSubmissionListSerializer,
    FormReportSummarySerializer,
)
from .selectors import get_form_for_owner


class FormReportPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class FormReportSummaryAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = FormReportSummarySerializer

    @extend_schema(responses=FormReportSummarySerializer)
    def get(self, request, form_id):
        summary = get_form_report_summary(owner=request.user, form_id=form_id)
        if summary is None:
            raise Http404
        return Response(self.get_serializer(summary).data)


class FormReportSubmissionListAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = FormReportSubmissionListSerializer
    pagination_class = FormReportPagination

    @extend_schema(responses=FormReportSubmissionListSerializer(many=True))
    def get(self, request, form_id):
        if get_form_for_owner(owner=request.user, form_id=form_id) is None:
            raise Http404

        queryset = get_form_report_submissions(
            owner=request.user,
            form_id=form_id,
        )
        page = self.paginate_queryset(queryset)
        payload = [submission_list_item(item) for item in page]
        serializer = self.get_serializer(payload, many=True)
        return self.get_paginated_response(serializer.data)


class FormReportSubmissionDetailAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = FormReportSubmissionDetailSerializer

    @extend_schema(responses=FormReportSubmissionDetailSerializer)
    def get(self, request, form_id, submission_public_id):
        detail = get_form_report_submission_detail(
            owner=request.user,
            form_id=form_id,
            submission_public_id=submission_public_id,
        )
        if detail is None:
            raise Http404
        return Response(self.get_serializer(detail).data)
