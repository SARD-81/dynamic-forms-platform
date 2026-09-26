from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    """Base entry point for API v1"""
    return Response(
        {"name": "Dynamic Forms Platform API Gate 3", "version": "1.0.0", "docs": "/api/v1/docs/"}
    )
