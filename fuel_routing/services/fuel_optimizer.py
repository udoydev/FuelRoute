import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


def optimize_fuel_stops(
    total_distance_miles: float,
    candidate_stations: List[Dict[str, Any]],
    max_range_miles: float = 500.0,
    mpg: float = 10.0
) -> Tuple[List[Dict[str, Any]], float, float]:
    """
    Optimizes fuel stops along a road trip route.

    Constraints:
      - Vehicle maximum range = 500 miles (Fuel capacity = 50 gallons @ 10 MPG).
      - Starts with a full tank (500 miles range).
      - Vehicle must never run out of fuel (distance between stops <= 500 miles).
      - Minimizes number of stops and total fuel cost.
      - Total fuel consumed = total_distance_miles / mpg.

    Returns:
      (selected_stops, total_fuel_cost, total_gallons_consumed)
    """
    total_gallons = round(total_distance_miles / mpg, 2)
    max_tank_gallons = max_range_miles / mpg # 50.0 gallons

    # Case 1: Route is within initial tank range (<= 500 miles)
    if total_distance_miles <= max_range_miles:
        if candidate_stations:
            cheapest = min(candidate_stations, key=lambda s: s["retail_price"])
            benchmark_price = cheapest["retail_price"]
        else:
            benchmark_price = 3.15  # Fallback US national average if no corridor station

        total_cost = round(total_gallons * benchmark_price, 2)
        return [], total_cost, total_gallons

    # Case 2: Multi-stop route (> 500 miles)
    valid_candidates = [
        s for s in candidate_stations
        if 5.0 <= s["distance_along_route"] <= (total_distance_miles - 5.0)
    ]

    # Cluster nearby stations (within 5-mile buckets along highway) to pick best price per interchange
    clustered: Dict[float, Dict[str, Any]] = {}
    for s in valid_candidates:
        bucket = round(s["distance_along_route"] / 5.0) * 5.0
        if bucket not in clustered or s["retail_price"] < clustered[bucket]["retail_price"]:
            clustered[bucket] = s

    stations = sorted(clustered.values(), key=lambda s: s["distance_along_route"])

    # Build DAG nodes: Start (0), Stations (1..N), Destination (N+1)
    nodes = [{"name": "Start", "distance": 0.0, "price": 0.0, "station": None}]
    for s in stations:
        nodes.append({
            "name": s["name"],
            "distance": s["distance_along_route"],
            "price": s["retail_price"],
            "station": s
        })

    dest_idx = len(nodes)
    nodes.append({
        "name": "Destination",
        "distance": total_distance_miles,
        "price": 0.0,
        "station": None
    })

    N = len(nodes)
    INF = float("inf")
    # State: dp[i] = (stops_count, total_cost)
    dp: List[Tuple[float, float]] = [(INF, INF)] * N
    parent: List[int] = [-1] * N
    dp[0] = (0, 0.0)

    # Relax edges in topological order (distance-ordered DAG)
    for i in range(N):
        stops_i, cost_i = dp[i]
        if stops_i == INF:
            continue

        d_i = nodes[i]["distance"]

        for j in range(i + 1, N):
            d_j = nodes[j]["distance"]
            gap = d_j - d_i

            # Cannot exceed vehicle max range on any single leg
            if gap > max_range_miles:
                break

            # Leg fuel cost:
            # If j is a station, the fuel consumed on this leg (gap/mpg) is replenished at station j's price.
            # If j is destination, remaining fuel was purchased at station i before driving to destination.
            if j == dest_idx:
                leg_price = nodes[i]["price"] if i > 0 else 3.15
                leg_cost = (gap / mpg) * leg_price
                new_stops = stops_i
            else:
                leg_price = nodes[j]["price"]
                leg_cost = (gap / mpg) * leg_price
                new_stops = stops_i + 1

            new_cost = cost_i + leg_cost
            candidate_state = (new_stops, new_cost)

            # Lexicographical minimization: prioritize fewest stops, then minimum cost
            if candidate_state < dp[j]:
                dp[j] = candidate_state
                parent[j] = i

    # Verify reachability
    if dp[dest_idx][0] == INF:
        raise ValueError(
            f"Unable to find a valid fueling route. There is a gap between stations that exceeds the "
            f"{max_range_miles}-mile vehicle range limit along the computed highway route."
        )

    # Reconstruct optimal path
    curr = dest_idx
    path: List[int] = []
    while curr != -1:
        path.append(curr)
        curr = parent[curr]
    path.reverse()

    # Build output fuel stop details
    selected_stops: List[Dict[str, Any]] = []
    prev_d = 0.0

    for idx in path[1:-1]:
        node = nodes[idx]
        st = dict(node["station"])
        gal_to_here = (node["distance"] - prev_d) / mpg

        # Never exceed tank capacity
        gal_to_here = min(gal_to_here, max_tank_gallons)

        stop_item = {
            "truckstop_id": st.get("opis_id"),
            "name": st.get("name"),
            "address": st.get("address"),
            "city": st.get("city"),
            "state": st.get("state"),
            "retail_price_per_gallon": round(st.get("retail_price", 0.0), 3),
            "gallons_purchased": round(gal_to_here, 2),
            "cost_at_stop": round(gal_to_here * st.get("retail_price", 0.0), 2),
            "distance_from_start_miles": round(node["distance"], 1),
            "coordinates": [st.get("lon"), st.get("lat")] # GeoJSON [lon, lat]
        }
        selected_stops.append(stop_item)
        prev_d = node["distance"]

    # Calculate exact total fuel cost for the trip (D / mpg)
    total_cost = round(dp[dest_idx][1], 2)
    return selected_stops, total_cost, total_gallons
