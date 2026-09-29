from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.participant_access import (
    ParticipantUnlockThrottleUnavailable,
    clear_participant_unlock_failures,
    grant_participant_access,
    has_participant_grant,
    participant_client_id,
    participant_unlock_retry_after_seconds,
    reserve_participant_unlock_attempt,
    verify_participant_password,
)
from apps.forms.models import Form

from .models import Process, ProcessRun
from .participant_selectors import (
    RESOURCE_TYPE,
    get_process_participant_read_model,
    get_published_process_by_public_id,
    increment_process_view_count,
)
from .participant_serializers import (
    ParticipantCompleteStepInputSerializer,
    ParticipantProcessRunDetailSerializer,
    ParticipantProcessSerializer,
    ParticipantUnlockSerializer,
)
from .services import complete_process_step_run, hash_resume_token, start_process_run


def _published_process_or_404(*, public_id):
    process = get_published_process_by_public_id(public_id=public_id)
    if process is None:
        raise Http404
    return process


def _executable_process_or_404(*, public_id):
    process = (
        Process.objects.filter(
            public_id=public_id,
            status__in=[Process.Status.PUBLISHED, Process.Status.CLOSED],
        )
        .select_related("category")
        .first()
    )
    if process is None:
        raise Http404

    if (
        process.visibility == Process.Visibility.PUBLIC
        and process.steps.filter(form__visibility=Form.Visibility.PRIVATE).exists()
    ):
        raise Http404

    return process


def _password_required_response():
    return Response(
        {
            "error_code": "PARTICIPANT_ACCESS_REQUIRED",
            "detail": "Participant access is required.",
        },
        status=status.HTTP_403_FORBIDDEN,
    )


def _rate_limited_response():
    response = Response(
        {
            "error_code": "PARTICIPANT_ACCESS_RATE_LIMITED",
            "detail": "Too many password attempts. Try again later.",
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
    response["Retry-After"] = str(participant_unlock_retry_after_seconds())
    return response


def _temporarily_unavailable_response():
    return Response(
        {
            "error_code": "PARTICIPANT_ACCESS_TEMPORARILY_UNAVAILABLE",
            "detail": "Password verification is temporarily unavailable. Try again later.",
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _validation_response(errors):
    return Response(
        {
            "error_code": "PROCESS_EXECUTION_VALIDATION_ERROR",
            "detail": "The process execution request is invalid.",
            "field_errors": errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _get_run_for_participant(*, process, run_public_id, request):
    run = (
        ProcessRun.objects.filter(process=process, public_id=run_public_id)
        .select_related("process")
        .prefetch_related("step_runs__process_step__form")
        .first()
    )
    if run is None:
        raise Http404

    if run.respondent_id is not None:
        if not request.user.is_authenticated or request.user.pk != run.respondent_id:
            return None, Response(
                {
                    "error_code": "PROCESS_RUN_ACCESS_DENIED",
                    "detail": "You do not have access to this process run.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
    else:
        raw_token = request.headers.get("X-Resume-Token")
        if raw_token:
            raw_token = raw_token.strip()

        if not raw_token or hash_resume_token(raw_token) != run.resume_token_hash:
            return None, Response(
                {
                    "error_code": "INVALID_RESUME_TOKEN",
                    "detail": "A valid X-Resume-Token header is required to access this run.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

    return run, None


class ParticipantProcessDetailAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]
    serializer_class = ParticipantProcessSerializer

    @extend_schema(responses=ParticipantProcessSerializer)
    def get(self, request, public_id):
        process = _published_process_or_404(public_id=public_id)
        if process.visibility == Process.Visibility.PRIVATE and not has_participant_grant(
            session=request.session,
            resource_type=RESOURCE_TYPE,
            public_id=process.public_id,
        ):
            return _password_required_response()

        read_model = get_process_participant_read_model(process=process)
        if request.method == "GET":
            increment_process_view_count(process_id=process.pk)
        return Response(ParticipantProcessSerializer(read_model).data)


class ParticipantProcessUnlockAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]
    serializer_class = ParticipantUnlockSerializer

    @extend_schema(request=ParticipantUnlockSerializer, responses={204: None, 429: None, 503: None})
    def post(self, request, public_id):
        process = _published_process_or_404(public_id=public_id)
        if process.visibility == Process.Visibility.PUBLIC:
            return Response(status=status.HTTP_204_NO_CONTENT)

        client_id = participant_client_id(request)
        limit_args = {
            "session": request.session,
            "resource_type": RESOURCE_TYPE,
            "public_id": process.public_id,
            "client_id": client_id,
        }
        try:
            if reserve_participant_unlock_attempt(**limit_args):
                return _rate_limited_response()
        except ParticipantUnlockThrottleUnavailable:
            return _temporarily_unavailable_response()

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return _password_required_response()

        if not verify_participant_password(
            password_hash=process.access_password_hash,
            password=serializer.validated_data["password"],
        ):
            return _password_required_response()

        try:
            clear_participant_unlock_failures(**limit_args)
        except ParticipantUnlockThrottleUnavailable:
            return _temporarily_unavailable_response()
        grant_participant_access(
            session=request.session,
            resource_type=RESOURCE_TYPE,
            public_id=process.public_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ParticipantProcessRunStartAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]
    serializer_class = ParticipantProcessRunDetailSerializer

    @extend_schema(responses={201: ParticipantProcessRunDetailSerializer})
    def post(self, request, public_id):
        process = _published_process_or_404(public_id=public_id)
        if process.visibility == Process.Visibility.PRIVATE and not has_participant_grant(
            session=request.session,
            resource_type=RESOURCE_TYPE,
            public_id=process.public_id,
        ):
            return _password_required_response()

        respondent = request.user if request.user.is_authenticated else None
        try:
            run, raw_token = start_process_run(
                process=process,
                respondent=respondent,
            )
        except DjangoValidationError as exc:
            errors = exc.message_dict if hasattr(exc, "message_dict") else {"process": exc.messages}
            return _validation_response(errors)

        run.resume_token = raw_token
        return Response(
            ParticipantProcessRunDetailSerializer(run).data,
            status=status.HTTP_201_CREATED,
        )


class ParticipantProcessRunDetailAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]
    serializer_class = ParticipantProcessRunDetailSerializer

    @extend_schema(responses={200: ParticipantProcessRunDetailSerializer})
    def get(self, request, public_id, run_public_id):
        process = _executable_process_or_404(public_id=public_id)
        if process.visibility == Process.Visibility.PRIVATE and not has_participant_grant(
            session=request.session,
            resource_type=RESOURCE_TYPE,
            public_id=process.public_id,
        ):
            return _password_required_response()

        run, error_response = _get_run_for_participant(
            process=process,
            run_public_id=run_public_id,
            request=request,
        )
        if error_response:
            return error_response

        return Response(
            ParticipantProcessRunDetailSerializer(run).data,
            status=status.HTTP_200_OK,
        )


class ParticipantProcessStepCompleteAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]
    serializer_class = ParticipantCompleteStepInputSerializer

    @extend_schema(
        request=ParticipantCompleteStepInputSerializer,
        responses={200: ParticipantProcessRunDetailSerializer},
    )
    def post(self, request, public_id, run_public_id, step_id):
        process = _executable_process_or_404(public_id=public_id)
        if process.visibility == Process.Visibility.PRIVATE and not has_participant_grant(
            session=request.session,
            resource_type=RESOURCE_TYPE,
            public_id=process.public_id,
        ):
            return _password_required_response()

        run, error_response = _get_run_for_participant(
            process=process,
            run_public_id=run_public_id,
            request=request,
        )
        if error_response:
            return error_response

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return _validation_response(serializer.errors)

        step_run = run.step_runs.filter(process_step_id=step_id).first()
        if step_run is None:
            raise Http404

        try:
            complete_process_step_run(
                process_run=run,
                step_run_id=step_run.pk,
                answers=serializer.validated_data["answers"],
                respondent=request.user if request.user.is_authenticated else None,
            )
        except DjangoValidationError as exc:
            errors = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return _validation_response(errors)

        run.refresh_from_db()
        return Response(
            ParticipantProcessRunDetailSerializer(run).data,
            status=status.HTTP_200_OK,
        )
