from django.urls import path

from .api_views import CategoryDetailAPIView, CategoryListCreateAPIView

app_name = "core_api"

urlpatterns = [
    path("", CategoryListCreateAPIView.as_view(), name="category-list"),
    path("<int:category_id>/", CategoryDetailAPIView.as_view(), name="category-detail"),
]
