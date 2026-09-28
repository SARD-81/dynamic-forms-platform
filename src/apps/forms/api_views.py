from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.integrations import form_has_active_process_runs

from .models import Form
from .selectors import get_form_for_owner, get_forms_for_owner
from .serializers import FormSerializer, FormWriteSerializer
from .services import (
    close_form,
    create_form,
    delete_draft_form,
    publish_form,
    update_draft_form,
)


def _field_errors_from_django_validation(exc):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return {"__all__": exc.messages}


def _validation_response(exc):
    return Response(
        {
            "error_code": "FORM_VALIDATION_ERROR",
            "detail": "Invalid form data or lifecycle operation.",
            "field_errors": _field_errors_from_django_validation(exc),
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _serializer_validation_response(serializer):
    return Response(
        {
            "error_code": "FORM_VALIDATION_ERROR",
            "detail": "Invalid form data or lifecycle operation.",
            "field_errors": serializer.errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _owned_form_or_404(*, owner, form_id):
    form = get_form_for_owner(owner=owner, form_id=form_id)
    if form is None:
        raise Http404
    return form


class FormListCreateAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = FormSerializer

    @extend_schema(responses=FormSerializer(many=True))
    def get(self, request):
        forms = get_forms_for_owner(owner=request.user)
        return Response(FormSerializer(forms, many=True).data)

    @extend_schema(request=FormWriteSerializer, responses={201: FormSerializer})
    def post(self, request):
        serializer = FormWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_validation_response(serializer)

        data = serializer.validated_data
        try:
            form = create_form(
                owner=request.user,
                title=data["title"],
                description=data.get("description", ""),
                category_id=data.get("category_id"),
                visibility=data.get("visibility", Form.Visibility.PUBLIC),
                access_password=data.get("access_password"),
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)

        return Response(FormSerializer(form).data, status=status.HTTP_201_CREATED)


class FormDetailAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = FormSerializer

    def get(self, request, form_id):
        form = _owned_form_or_404(owner=request.user, form_id=form_id)
        return Response(FormSerializer(form).data)

    @extend_schema(request=FormWriteSerializer, responses=FormSerializer)
    def patch(self, request, form_id):
        form = _owned_form_or_404(owner=request.user, form_id=form_id)
        serializer = FormWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return _serializer_validation_response(serializer)

        data = serializer.validated_data
        update_fields = {
            field: data[field]
            for field in (
                "title",
                "description",
                "category_id",
                "visibility",
                "access_password",
            )
            if field in data
        }

        try:
            form = update_draft_form(
                form=form,
                owner=request.user,
                **update_fields,
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)

        return Response(FormSerializer(form).data)

    @extend_schema(responses={204: None})
    def delete(self, request, form_id):
        form = _owned_form_or_404(owner=request.user, form_id=form_id)
        try:
            delete_draft_form(form=form, owner=request.user)
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FormPublishAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = FormSerializer

    @extend_schema(request=None, responses=FormSerializer)
    def post(self, request, form_id):
        form = _owned_form_or_404(owner=request.user, form_id=form_id)
        try:
            form = publish_form(form=form, owner=request.user)
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(FormSerializer(form).data)


class FormCloseAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = FormSerializer

    @extend_schema(request=None, responses=FormSerializer)
    def post(self, request, form_id):
        form = _owned_form_or_404(owner=request.user, form_id=form_id)
        try:
            form = close_form(
                form=form,
                owner=request.user,
                active_run_checker=form_has_active_process_runs,
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(FormSerializer(form).data)
