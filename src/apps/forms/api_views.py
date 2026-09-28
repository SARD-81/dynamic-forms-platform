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
from .selectors import (
    get_form_for_owner,
    get_forms_for_owner,
    get_option_for_owner,
    get_options_for_question_owner,
    get_question_for_owner,
    get_questions_for_form_owner,
)
from .serializers import (
    FormSerializer,
    FormWriteSerializer,
    QuestionOptionReorderSerializer,
    QuestionOptionSerializer,
    QuestionOptionWriteSerializer,
    QuestionReorderSerializer,
    QuestionSerializer,
    QuestionWriteSerializer,
)
from .services import (
    close_form,
    create_form,
    create_question,
    create_question_option,
    delete_draft_form,
    delete_question,
    delete_question_option,
    publish_form,
    reorder_question_options,
    reorder_questions,
    update_draft_form,
    update_question,
    update_question_option,
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


def _owned_question_or_404(*, owner, form_id, question_id):
    question = get_question_for_owner(
        owner=owner,
        form_id=form_id,
        question_id=question_id,
    )
    if question is None:
        raise Http404
    return question


def _owned_option_or_404(*, owner, form_id, question_id, option_id):
    option = get_option_for_owner(
        owner=owner,
        form_id=form_id,
        question_id=question_id,
        option_id=option_id,
    )
    if option is None:
        raise Http404
    return option


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


class QuestionListCreateAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionSerializer

    @extend_schema(responses=QuestionSerializer(many=True))
    def get(self, request, form_id):
        _owned_form_or_404(owner=request.user, form_id=form_id)
        questions = get_questions_for_form_owner(owner=request.user, form_id=form_id)
        return Response(QuestionSerializer(questions, many=True).data)

    @extend_schema(request=QuestionWriteSerializer, responses={201: QuestionSerializer})
    def post(self, request, form_id):
        form = _owned_form_or_404(owner=request.user, form_id=form_id)
        serializer = QuestionWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_validation_response(serializer)

        try:
            question = create_question(
                form=form,
                owner=request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(
            QuestionSerializer(question).data,
            status=status.HTTP_201_CREATED,
        )


class QuestionReorderAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionReorderSerializer

    @extend_schema(request=QuestionReorderSerializer, responses=QuestionSerializer(many=True))
    def post(self, request, form_id):
        form = _owned_form_or_404(owner=request.user, form_id=form_id)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_validation_response(serializer)
        try:
            questions = reorder_questions(
                form=form,
                owner=request.user,
                question_ids=serializer.validated_data["question_ids"],
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(QuestionSerializer(questions, many=True).data)


class QuestionDetailAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionSerializer

    def get(self, request, form_id, question_id):
        question = _owned_question_or_404(
            owner=request.user,
            form_id=form_id,
            question_id=question_id,
        )
        return Response(QuestionSerializer(question).data)

    @extend_schema(request=QuestionWriteSerializer, responses=QuestionSerializer)
    def patch(self, request, form_id, question_id):
        question = _owned_question_or_404(
            owner=request.user,
            form_id=form_id,
            question_id=question_id,
        )
        serializer = QuestionWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return _serializer_validation_response(serializer)

        update_fields = {
            field: serializer.validated_data[field]
            for field in (
                "text",
                "question_type",
                "is_required",
                "max_length",
                "min_value",
                "max_value",
            )
            if field in serializer.validated_data
        }
        try:
            question = update_question(
                question=question,
                owner=request.user,
                **update_fields,
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(QuestionSerializer(question).data)

    @extend_schema(responses={204: None})
    def delete(self, request, form_id, question_id):
        question = _owned_question_or_404(
            owner=request.user,
            form_id=form_id,
            question_id=question_id,
        )
        try:
            delete_question(question=question, owner=request.user)
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuestionOptionListCreateAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionOptionSerializer

    @extend_schema(responses=QuestionOptionSerializer(many=True))
    def get(self, request, form_id, question_id):
        _owned_question_or_404(
            owner=request.user,
            form_id=form_id,
            question_id=question_id,
        )
        options = get_options_for_question_owner(
            owner=request.user,
            form_id=form_id,
            question_id=question_id,
        )
        return Response(QuestionOptionSerializer(options, many=True).data)

    @extend_schema(
        request=QuestionOptionWriteSerializer,
        responses={201: QuestionOptionSerializer},
    )
    def post(self, request, form_id, question_id):
        question = _owned_question_or_404(
            owner=request.user,
            form_id=form_id,
            question_id=question_id,
        )
        serializer = QuestionOptionWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_validation_response(serializer)
        try:
            option = create_question_option(
                question=question,
                owner=request.user,
                label=serializer.validated_data["label"],
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(
            QuestionOptionSerializer(option).data,
            status=status.HTTP_201_CREATED,
        )


class QuestionOptionReorderAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionOptionReorderSerializer

    @extend_schema(
        request=QuestionOptionReorderSerializer,
        responses=QuestionOptionSerializer(many=True),
    )
    def post(self, request, form_id, question_id):
        question = _owned_question_or_404(
            owner=request.user,
            form_id=form_id,
            question_id=question_id,
        )
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_validation_response(serializer)
        try:
            options = reorder_question_options(
                question=question,
                owner=request.user,
                option_ids=serializer.validated_data["option_ids"],
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(QuestionOptionSerializer(options, many=True).data)


class QuestionOptionDetailAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionOptionSerializer

    def get(self, request, form_id, question_id, option_id):
        option = _owned_option_or_404(
            owner=request.user,
            form_id=form_id,
            question_id=question_id,
            option_id=option_id,
        )
        return Response(QuestionOptionSerializer(option).data)

    @extend_schema(
        request=QuestionOptionWriteSerializer,
        responses=QuestionOptionSerializer,
    )
    def patch(self, request, form_id, question_id, option_id):
        option = _owned_option_or_404(
            owner=request.user,
            form_id=form_id,
            question_id=question_id,
            option_id=option_id,
        )
        serializer = QuestionOptionWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return _serializer_validation_response(serializer)
        try:
            option = update_question_option(
                option=option,
                owner=request.user,
                label=serializer.validated_data["label"],
            )
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(QuestionOptionSerializer(option).data)

    @extend_schema(responses={204: None})
    def delete(self, request, form_id, question_id, option_id):
        option = _owned_option_or_404(
            owner=request.user,
            form_id=form_id,
            question_id=question_id,
            option_id=option_id,
        )
        try:
            delete_question_option(option=option, owner=request.user)
        except DjangoValidationError as exc:
            return _validation_response(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)
