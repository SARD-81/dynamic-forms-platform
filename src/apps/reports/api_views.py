from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework import status

from .models import ReportSubscription
from .selectors import get_report_subscription, get_report_subscriptions
from .serializers import (
    PeriodicReportPayloadSerializer,
    ReportSubscriptionSerializer,
    ReportSubscriptionWriteSerializer,
)
from .services import (
    create_report_subscription,
    deactivate_report_subscription,
    generate_periodic_report_payload,
    update_report_subscription,
)


class IsSiteStaff(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
        )


def _service_error(exc):
    detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
    return Response(detail, status=status.HTTP_400_BAD_REQUEST)


class ReportSubscriptionListCreateAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsSiteStaff]

    @extend_schema(responses=ReportSubscriptionSerializer(many=True))
    def get(self, request):
        return Response(ReportSubscriptionSerializer(get_report_subscriptions(), many=True).data)

    @extend_schema(
        request=ReportSubscriptionWriteSerializer,
        responses={201: ReportSubscriptionSerializer},
    )
    def post(self, request):
        serializer = ReportSubscriptionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            subscription = create_report_subscription(actor=request.user, **serializer.validated_data)
        except DjangoValidationError as exc:
            return _service_error(exc)
        return Response(ReportSubscriptionSerializer(subscription).data, status=status.HTTP_201_CREATED)


class ReportSubscriptionDetailAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsSiteStaff]

    def _get_object(self, subscription_id):
        subscription = get_report_subscription(subscription_id=subscription_id)
        if subscription is None:
            raise Http404
        return subscription

    @extend_schema(responses=ReportSubscriptionSerializer)
    def get(self, request, subscription_id):
        return Response(ReportSubscriptionSerializer(self._get_object(subscription_id)).data)

    @extend_schema(request=ReportSubscriptionWriteSerializer, responses=ReportSubscriptionSerializer)
    def put(self, request, subscription_id):
        subscription = self._get_object(subscription_id)
        serializer = ReportSubscriptionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            subscription = update_report_subscription(
                actor=request.user,
                subscription_id=subscription.pk,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            return _service_error(exc)
        return Response(ReportSubscriptionSerializer(subscription).data)


class ReportSubscriptionDeactivateAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsSiteStaff]

    @extend_schema(request=None, responses=ReportSubscriptionSerializer)
    def post(self, request, subscription_id):
        if get_report_subscription(subscription_id=subscription_id) is None:
            raise Http404
        subscription = deactivate_report_subscription(
            actor=request.user,
            subscription_id=subscription_id,
        )
        return Response(ReportSubscriptionSerializer(subscription).data)


class PeriodicReportPreviewAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsSiteStaff]

    @extend_schema(responses=PeriodicReportPayloadSerializer)
    def get(self, request):
        frequency = request.query_params.get("frequency", ReportSubscription.Frequency.WEEKLY)
        if frequency not in ReportSubscription.Frequency.values:
            return Response({"frequency": ["Unsupported report frequency."]}, status=400)
        payload = generate_periodic_report_payload(frequency=frequency)
        return Response(PeriodicReportPayloadSerializer(payload).data)
