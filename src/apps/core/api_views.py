from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .selectors import get_category_choices_for_owner, get_category_for_owner
from .serializers import CategorySerializer
from .services import create_category, delete_category, rename_category


def _field_errors_from_django_validation(exc):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return {"__all__": exc.messages}


def _category_validation_response(errors):
    return Response(
        {
            "error_code": "CATEGORY_VALIDATION_ERROR",
            "detail": "Invalid category data.",
            "field_errors": errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    """Base entry point for API v1"""
    return Response(
        {
            "name": "Dynamic Forms Platform API Gate 3",
            "version": "1.0.0",
            "docs": "/api/v1/docs/",
            "categories": "/api/v1/categories/",
        }
    )


class CategoryListCreateAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CategorySerializer

    def get(self, request):
        categories = get_category_choices_for_owner(owner=request.user)
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return _category_validation_response(serializer.errors)

        try:
            category = create_category(
                owner=request.user,
                name=serializer.validated_data["name"],
            )
        except DjangoValidationError as exc:
            return _category_validation_response(_field_errors_from_django_validation(exc))

        return Response(
            self.get_serializer(category).data,
            status=status.HTTP_201_CREATED,
        )


class CategoryDetailAPIView(GenericAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CategorySerializer

    def _get_category(self, request, category_id):
        category = get_category_for_owner(
            owner=request.user,
            category_id=category_id,
        )
        if category is None:
            raise Http404
        return category

    def get(self, request, category_id):
        category = self._get_category(request, category_id)
        return Response(self.get_serializer(category).data)

    def patch(self, request, category_id):
        category = self._get_category(request, category_id)
        serializer = self.get_serializer(category, data=request.data, partial=True)
        if not serializer.is_valid():
            return _category_validation_response(serializer.errors)

        name = serializer.validated_data.get("name", category.name)
        try:
            category = rename_category(
                category=category,
                owner=request.user,
                name=name,
            )
        except DjangoValidationError as exc:
            return _category_validation_response(_field_errors_from_django_validation(exc))

        return Response(self.get_serializer(category).data)

    def delete(self, request, category_id):
        category = self._get_category(request, category_id)
        delete_category(category=category, owner=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
