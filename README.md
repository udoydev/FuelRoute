# ⚡ FuelRoute — Optimal US Highway Fuel Routing Engine

A high-performance Django REST Framework API that calculates the optimal driving route between any two locations in the USA and determines cost-effective fuel stops based on retail fuel prices, under a vehicle maximum range constraint of 500 miles at 10 MPG.

---

## 🌟 Key Features

1. **Optimal Fuel Planning**:
   - Adheres to a strict **500-mile vehicle range** constraint (50-gallon tank @ 10 MPG).
   - Minimizes total fuel expenditure using a **Directed Acyclic Graph (DAG) shortest-path optimization algorithm**.
   - Ensures no single segment between stops (or from start / to destination) ever exceeds 500 miles.

2. **Single Routing API Call (Zero Key Needed)**:
   - Fetches driving route geometry, duration, and highway mileage from **OSRM (Open Source Routing Machine)** in **exactly 1 HTTP call**.
   - No paid subscription, API key, or credit card required.

3. **Sub-Millisecond Spatial Indexing**:
   - Geocodes and indexes over **6,600+ US truckstops** from the OPIS dataset into an in-memory spherical **3D $c\text{KD-Tree}$**.
   - Filters candidate fuel stations within a highway buffer corridor in **< 4 milliseconds**.

4. **Dual Output (API + Interactive Map)**:
   - **REST API (`/api/route/`)**: Returns route metrics, fuel stop details, and complete GeoJSON feature collections.
   - **Interactive Web UI (`/`)**: Built with Leaflet.js and OpenStreetMap to visually inspect routes, elevation, and fuel stops with interactive popup pricing.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11+ / Django 5.1 / Django REST Framework
- **Spatial Processing**: SciPy (`scipy.spatial.cKDTree`), NumPy (vectorized spherical coordinates)
- **Routing Engine**: OSRM (Open Source Routing Machine API — 1 call)
- **Geocoding**: Local US places database with OpenStreetMap Nominatim/Photon fallback
- **Frontend Map**: Leaflet.js / CartoDB Voyager tiles / Vanilla CSS

---

## 🚀 Quick Start (Local Setup)

### 1. Clone & Set Up Virtual Environment

```bash
git clone <your-repo-url>
cd fuel_optimizer

python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Apply Migrations & Run Server

```bash
python manage.py migrate
python manage.py runserver
```

Now open:
- **Interactive Map UI**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **API Endpoint**: [http://127.0.0.1:8000/api/route/](http://127.0.0.1:8000/api/route/)

---

## 🐳 Docker Setup

```bash
# Build and run with Docker Compose
docker compose up --build
```
Access at [http://localhost:8000/](http://localhost:8000/).

---

## 🧪 Running Automated Tests

```bash
python manage.py test tests -v 2
```
All 14 tests verify:
- 500-mile vehicle range constraint enforcement.
- Trips under 500 miles requiring zero stops.
- Long cross-country multi-stop optimization (e.g. NY to LA).
- Coordinate & city name geocoding.
- Spatial index station queries.
- API validation and error responses.

---

## 📖 API Documentation

### `POST /api/route/`
**Headers**: `Content-Type: application/json`

#### Request Payload:
```json
{
  "start": "Austin, TX",
  "finish": "Nashville, TN"
}
```
*(Also supports raw coordinates: `{"start": "30.2672,-97.7431", "finish": "36.1627,-86.7816"}`)*

#### Response (`200 OK`):
```json
{
  "status": "success",
  "route_summary": {
    "start_location": "Austin, Travis County, Texas, United States",
    "finish_location": "Nashville, Davidson County, Tennessee, United States",
    "total_distance_miles": 858.25,
    "estimated_duration": "15 hr 3 min",
    "total_gallons_consumed": 85.83,
    "total_fuel_cost": 245.22,
    "fuel_stops_count": 1,
    "vehicle_mpg": 10.0,
    "vehicle_max_range_miles": 500.0
  },
  "fuel_stops": [
    {
      "truckstop_id": 7900,
      "name": "Quiktrip #7900",
      "address": "I-30 & FM-989",
      "city": "Texarkana",
      "state": "TX",
      "retail_price_per_gallon": 2.857,
      "gallons_purchased": 85.82,
      "cost_at_stop": 245.22,
      "distance_from_start_miles": 358.7,
      "coordinates": [-94.137, 33.435]
    }
  ],
  "map_geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": { "type": "LineString", "coordinates": [...] },
        "properties": { "name": "Optimal Driving Route" }
      },
      {
        "type": "Feature",
        "geometry": { "type": "Point", "coordinates": [-97.743, 30.267] },
        "properties": { "marker_type": "start", "name": "Origin" }
      },
      {
        "type": "Feature",
        "geometry": { "type": "Point", "coordinates": [-86.781, 36.162] },
        "properties": { "marker_type": "finish", "name": "Destination" }
      },
      {
        "type": "Feature",
        "geometry": { "type": "Point", "coordinates": [-94.137, 33.435] },
        "properties": {
          "marker_type": "fuel_stop",
          "stop_number": 1,
          "name": "Quiktrip #7900",
          "retail_price_per_gallon": 2.857
        }
      }
    ]
  }
}
```

---

## 📬 Postman Collection

Import `postman_collection.json` into Postman to test:
1. `Austin, TX` to `Nashville, TN` (Multi-stop)
2. `New York, NY` to `Los Angeles, CA` (Cross-country)
3. `Austin, TX` to `San Antonio, TX` (Short trip < 500 mi)
4. `GET` query parameter endpoint
5. Error handling and validation

---

