from django.urls import path
from .views import RouteOptimizationAPIView, map_view

urlpatterns = [
    # Interactive Map Visualizer
    path("", map_view, name="map-view"),
    path("map/", map_view, name="map-view-alias"),

    # REST API Endpoint
    path("api/route/", RouteOptimizationAPIView.as_view(), name="api-route"),
]
