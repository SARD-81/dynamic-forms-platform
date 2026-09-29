from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.participant_access import (
    clear_participant_unlock_failures,
    grant_participant_access,
    has_participant_grant,
    is_participant_unlock_rate_limited,
    participant_client_id,
    participant_unlock_retry_after_seconds,
    record_participant_unlock_failure,
    verify_participant_password,
)

from .models import Form
from .participant_selectors import (
    RESOURCE_TYPE,
    get_form_participant_read_model,
    get_published_form_by_public_id,
    increment_form_view_count,
)
from .participant_serializers import ParticipantFormSerializer, ParticipantUnlockSerializer


def _published_form_or_404(*, public_id):
    form = get_published_form_by_public_id(public_id=public_id)
    if form is None:
        raise Http404
    return form


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


class ParticipantFormDetailAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]
    serializer_class = ParticipantFormSerializer

    @extend_schema(responses=ParticipantFormSerializer)
    def get(self, request, public_id):
        form = _published_form_or_404(public_id=public_id)
        if form.visibility == Form.Visibility.PRIVATE and not has_participant_grant(
            session=request.session,
            resource_type=RESOURCE_TYPE,
            public_id=form.public_id,
        ):
            return _password_required_response()

        read_model = get_form_participant_read_model(form=form)
        if request.method == "GET":
            increment_form_view_count(form_id=form.pk)
        return Response(ParticipantFormSerializer(read_model).data)


class ParticipantFormUnlockAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]
    serializer_class = ParticipantUnlockSerializer

    @extend_schema(request=ParticipantUnlockSerializer, responses={204: None, 429: None, 503: None})
    def post(self, request, public_id):
        form = _published_form_or_404(public_id=public_id)
        if form.visibility == Form.Visibility.PUBLIC:
            return Response(status=status.HTTP_204_NO_CONTENT)

        client_id = participant_client_id(request)
        limit_args = {
            "session": request.session,
            "resource_type": RESOURCE_TYPE,
            "public_id": form.public_id,
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
            password_hash=form.access_password_hash,
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
            public_id=form.public_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
