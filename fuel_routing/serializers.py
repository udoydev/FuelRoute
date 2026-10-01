from rest_framework import serializers


class RouteRequestSerializer(serializers.Serializer):
    start = serializers.CharField(
        required=True,
        help_text="Starting location in the USA (e.g., 'Austin, TX' or '30.2672,-97.7431')"
    )
    finish = serializers.CharField(
        required=True,
        help_text="Destination location in the USA (e.g., 'Nashville, TN' or '36.1627,-86.7816')"
    )

    def validate(self, attrs):
        start = attrs.get("start", "").strip()
        finish = attrs.get("finish", "").strip()
        if not start:
            raise serializers.ValidationError({"start": "Start location cannot be empty."})
        if not finish:
            raise serializers.ValidationError({"finish": "Finish location cannot be empty."})
        if start.lower() == finish.lower():
            raise serializers.ValidationError("Start and finish locations cannot be identical.")
        return attrs


class FuelStopSerializer(serializers.Serializer):
    truckstop_id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    retail_price_per_gallon = serializers.FloatField()
    gallons_purchased = serializers.FloatField()
    cost_at_stop = serializers.FloatField()
    distance_from_start_miles = serializers.FloatField()
    coordinates = serializers.ListField(
        child=serializers.FloatField(),
        min_length=2,
        max_length=2,
        help_text="[longitude, latitude]"
    )


class RouteSummarySerializer(serializers.Serializer):
    start_location = serializers.CharField()
    finish_location = serializers.CharField()
    routing_provider = serializers.CharField(required=False, default="OpenRouteService")
    total_distance_miles = serializers.FloatField()
    estimated_duration = serializers.CharField()
    total_gallons_consumed = serializers.FloatField()
    total_fuel_cost = serializers.FloatField()
    fuel_stops_count = serializers.IntegerField()
    vehicle_mpg = serializers.FloatField()
    vehicle_max_range_miles = serializers.FloatField()


class RouteResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    route_summary = RouteSummarySerializer()
    fuel_stops = FuelStopSerializer(many=True)
    map_geojson = serializers.DictField(help_text="GeoJSON FeatureCollection for route and stops")
