import logging
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import RouteRequestSerializer, RouteResponseSerializer
from .services.geocoding import geocode_location
from .services.routing_client import fetch_route_osrm
from .services.spatial_index import FuelStationSpatialIndex
from .services.fuel_optimizer import optimize_fuel_stops

logger = logging.getLogger(__name__)


def build_route_geojson(
    route_coordinates: list,
    start_info: tuple,
    finish_info: tuple,
    fuel_stops: list
) -> dict:
    """
    Constructs a complete GeoJSON FeatureCollection containing:
      1. Route LineString
      2. Start location point
      3. Finish location point
      4. Selected fuel stop markers with pricing metadata
    """
    features = [
        # Route path
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": route_coordinates # [[lon, lat], ...]
            },
            "properties": {
                "name": "Optimal Driving Route",
                "stroke": "#2563EB",
                "stroke-width": 5,
                "stroke-opacity": 0.85
            }
        },
        # Start marker
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [start_info[1], start_info[0]]
            },
            "properties": {
                "marker_type": "start",
                "name": "Origin",
                "location": start_info[2]
            }
        },
        # Finish marker
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [finish_info[1], finish_info[0]]
            },
            "properties": {
                "marker_type": "finish",
                "name": "Destination",
                "location": finish_info[2]
            }
        }
    ]

    # Add each optimal fuel stop marker
    for idx, stop in enumerate(fuel_stops, start=1):
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": stop["coordinates"] # [lon, lat]
            },
            "properties": {
                "marker_type": "fuel_stop",
                "stop_number": idx,
                "truckstop_id": stop["truckstop_id"],
                "name": stop["name"],
                "address": stop["address"],
                "city": stop["city"],
                "state": stop["state"],
                "retail_price_per_gallon": stop["retail_price_per_gallon"],
                "gallons_purchased": stop["gallons_purchased"],
                "cost_at_stop": stop["cost_at_stop"],
                "distance_from_start_miles": stop["distance_from_start_miles"]
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


class RouteOptimizationAPIView(APIView):
    """
    API endpoint to calculate optimal driving routes and fuel stops in the USA.
    Accepts GET (query parameters) and POST (JSON body).
    """

    def get(self, request):
        start = request.query_params.get("start")
        finish = request.query_params.get("finish")
        serializer = RouteRequestSerializer(data={"start": start, "finish": finish})
        if not serializer.is_valid():
            return Response(
                {"status": "error", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        return self._process_route(serializer.validated_data)

    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"status": "error", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        return self._process_route(serializer.validated_data)

    def _process_route(self, data: dict):
        start_query = data["start"]
        finish_query = data["finish"]

        try:
            # Step 1: Geocode start & finish locations
            start_lat, start_lon, start_name = geocode_location(start_query)
            finish_lat, finish_lon, finish_name = geocode_location(finish_query)

            # Step 2: Fetch route from OSRM (1 single HTTP call)
            route_result = fetch_route_osrm(start_lat, start_lon, finish_lat, finish_lon)
            total_distance = route_result["total_distance_miles"]
            route_coords = route_result["coordinates"]
            cumulative_dists = route_result["cumulative_distances"]
            duration_formatted = route_result["duration_formatted"]

            # Step 3: Query spatial index for candidate fuel stations along route
            spatial_index = FuelStationSpatialIndex.get_instance()
            candidates = spatial_index.find_candidate_stations(
                route_coordinates=route_coords,
                cumulative_distances=cumulative_dists,
                corridor_radius_miles=10.0
            )

            # Step 4: Run optimal fuel decision engine
            fuel_stops, total_cost, total_gallons = optimize_fuel_stops(
                total_distance_miles=total_distance,
                candidate_stations=candidates,
                max_range_miles=500.0,
                mpg=10.0
            )

            # Step 5: Build GeoJSON representation
            map_geojson = build_route_geojson(
                route_coordinates=route_coords,
                start_info=(start_lat, start_lon, start_name),
                finish_info=(finish_lat, finish_lon, finish_name),
                fuel_stops=fuel_stops
            )

            response_data = {
                "status": "success",
                "route_summary": {
                    "start_location": start_name,
                    "finish_location": finish_name,
                    "total_distance_miles": total_distance,
                    "estimated_duration": duration_formatted,
                    "total_gallons_consumed": total_gallons,
                    "total_fuel_cost": total_cost,
                    "fuel_stops_count": len(fuel_stops),
                    "vehicle_mpg": 10.0,
                    "vehicle_max_range_miles": 500.0
                },
                "fuel_stops": fuel_stops,
                "map_geojson": map_geojson
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ConnectionError as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.exception("Unexpected error during route optimization")
            return Response(
                {"status": "error", "message": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def map_view(request):
    """Renders the interactive web application interface for visual testing."""
    return render(request, "fuel_routing/map.html")
