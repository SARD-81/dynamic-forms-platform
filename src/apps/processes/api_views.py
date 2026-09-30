from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .selectors import (
    get_process_for_owner,
    get_process_step_for_owner,
    get_process_steps_for_owner,
    get_processes_for_owner,
)
from .serializers import (
    ProcessSerializer,
    ProcessStepReorderSerializer,
    ProcessStepSerializer,
    ProcessStepWriteSerializer,
    ProcessUpdateSerializer,
    ProcessWriteSerializer,
)
from .services import (
    close_process,
    create_process,
    create_process_step,
    delete_draft_process,
    delete_process_step,
    publish_process,
    reorder_process_steps,
    update_draft_process,
)


def _field_errors_from_django_validation(exc):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return {"__all__": exc.messages}


def _validation_response(exc):
    return Response(
        {
            "error_code": "PROCESS_VALIDATION_ERROR",
            "detail": "Invalid process data or lifecycle operation.",
            "field_errors": _field_errors_from_django_validation(exc),
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _serializer_validation_response(serializer):
    return Response(
        {
            "error_code": "PROCESS_VALIDATION_ERROR",
            "detail": "Invalid process data or lifecycle operation.",
            "field_errors": serializer.errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _owned_process_or_404(*, owner, process_id):
    process = get_process_for_owner(owner=owner, process_id=process_id)
    if process is None:
        raise Http404
    return process


def _owned_step_or_404(*, owner, process_id, step_id):
    step = get_process_step_for_owner(
        owner=owner,
        process_id=process_id,
        step_id=step_id,
    )
    if step is None:
        raise Http404
    return step


class ProcessListCreateAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessSerializer

    @extend_schema(responses=ProcessSerializer(many=True))
    def get(self, request):
        processes = get_processes_for_owner(owner=request.user)
        return Response(ProcessSerializer(processes, many=True).data)

    @extend_schema(request=ProcessWriteSerializer, responses={201: ProcessSerializer})
    def post(self, request):
        serializer = ProcessWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_validation_response(serializer)

        try:
            process = create_process(owner=request.user, **serializer.validated_data)
        except DjangoValidationError as exc:
            return _validation_response(exc)

        refreshed = get_process_for_owner(owner=request.user, process_id=process.pk)
        return Response(ProcessSerializer(refreshed).data, status=status.HTTP_201_CREATED)


class ProcessDetailAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessSerializer

    def get(self, request, process_id):
        process = _owned_process_or_404(owner=request.user, process_id=process_id)
        return Response(ProcessSerializer(process).data)

    @extend_schema(request=ProcessUpdateSerializer, responses=ProcessSerializer)
    def patch(self, request, process_id):
        process = _owned_process_or_404(owner=request.user, process_id=process_id)
        serializer = ProcessUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return _serializer_validation_response(serializer)

        try:
            update_draft_process(
                process=process,
                owner=request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)

        refreshed = get_process_for_owner(owner=request.user, process_id=process.pk)
        return Response(ProcessSerializer(refreshed).data)

    def delete(self, request, process_id):
        process = _owned_process_or_404(owner=request.user, process_id=process_id)
        try:
            delete_draft_process(process=process, owner=request.user)
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProcessPublishAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessSerializer

    @extend_schema(request=None, responses=ProcessSerializer)
    def post(self, request, process_id):
        process = _owned_process_or_404(owner=request.user, process_id=process_id)
        try:
            published_process = publish_process(process=process, owner=request.user)
        except DjangoValidationError as exc:
            return _validation_response(exc)

        refreshed = get_process_for_owner(owner=request.user, process_id=published_process.pk)
        return Response(ProcessSerializer(refreshed).data)


class ProcessCloseAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessSerializer

    @extend_schema(request=None, responses=ProcessSerializer)
    def post(self, request, process_id):
        process = _owned_process_or_404(owner=request.user, process_id=process_id)
        try:
            closed_process = close_process(process=process, owner=request.user)
        except DjangoValidationError as exc:
            return _validation_response(exc)

        refreshed = get_process_for_owner(owner=request.user, process_id=closed_process.pk)
        return Response(ProcessSerializer(refreshed).data)


class ProcessStepListCreateAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessStepSerializer

    @extend_schema(responses=ProcessStepSerializer(many=True))
    def get(self, request, process_id):
        _owned_process_or_404(owner=request.user, process_id=process_id)
        steps = get_process_steps_for_owner(owner=request.user, process_id=process_id)
        return Response(ProcessStepSerializer(steps, many=True).data)

    @extend_schema(request=ProcessStepWriteSerializer, responses={201: ProcessStepSerializer})
    def post(self, request, process_id):
        process = _owned_process_or_404(owner=request.user, process_id=process_id)
        serializer = ProcessStepWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_validation_response(serializer)

        try:
            step = create_process_step(
                process=process,
                owner=request.user,
                form_id=serializer.validated_data["form_id"],
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)

        refreshed = get_process_step_for_owner(
            owner=request.user,
            process_id=process.pk,
            step_id=step.pk,
        )
        return Response(ProcessStepSerializer(refreshed).data, status=status.HTTP_201_CREATED)


class ProcessStepDetailAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessStepSerializer

    def get(self, request, process_id, step_id):
        step = _owned_step_or_404(owner=request.user, process_id=process_id, step_id=step_id)
        return Response(ProcessStepSerializer(step).data)

    def delete(self, request, process_id, step_id):
        process = _owned_process_or_404(owner=request.user, process_id=process_id)
        _owned_step_or_404(owner=request.user, process_id=process_id, step_id=step_id)

        try:
            delete_process_step(process=process, owner=request.user, step_id=step_id)
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProcessStepReorderAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessStepReorderSerializer

    @extend_schema(request=ProcessStepReorderSerializer, responses=ProcessStepSerializer(many=True))
    def post(self, request, process_id):
        process = _owned_process_or_404(owner=request.user, process_id=process_id)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_validation_response(serializer)

        try:
            steps = reorder_process_steps(
                process=process,
                owner=request.user,
                step_ids=serializer.validated_data["step_ids"],
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(ProcessStepSerializer(steps, many=True).data)
