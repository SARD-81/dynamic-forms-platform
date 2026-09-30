from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .report_selectors import (
    get_process_report_run_detail,
    get_process_report_runs,
    get_process_report_summary,
    process_run_list_item,
)
from .report_serializers import (
    ProcessReportRunDetailSerializer,
    ProcessReportRunListSerializer,
    ProcessReportSummarySerializer,
)
from .selectors import get_process_for_owner


class ProcessReportPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ProcessReportSummaryAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessReportSummarySerializer

    @extend_schema(responses=ProcessReportSummarySerializer)
    def get(self, request, process_id):
        summary = get_process_report_summary(owner=request.user, process_id=process_id)
        if summary is None:
            raise Http404
        return Response(self.get_serializer(summary).data)


class ProcessReportRunListAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessReportRunListSerializer
    pagination_class = ProcessReportPagination

    @extend_schema(responses=ProcessReportRunListSerializer(many=True))
    def get(self, request, process_id):
        if get_process_for_owner(owner=request.user, process_id=process_id) is None:
            raise Http404

        queryset = get_process_report_runs(owner=request.user, process_id=process_id)
        page = self.paginate_queryset(queryset)
        payload = [process_run_list_item(item) for item in page]
        serializer = self.get_serializer(payload, many=True)
        return self.get_paginated_response(serializer.data)


class ProcessReportRunDetailAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessReportRunDetailSerializer

    @extend_schema(responses=ProcessReportRunDetailSerializer)
    def get(self, request, process_id, run_public_id):
        detail = get_process_report_run_detail(
            owner=request.user,
            process_id=process_id,
            run_public_id=run_public_id,
        )
        if detail is None:
            raise Http404
        return Response(self.get_serializer(detail).data)
