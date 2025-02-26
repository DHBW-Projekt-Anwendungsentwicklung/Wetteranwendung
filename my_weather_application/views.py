from django.shortcuts import render
import math
from django.http import JsonResponse
from .station_data import STATIONS  # Import der geladenen Wetterstationen


def my_weather_application(request):
    return render(request, 'frontend.html')


def haversine(lat1, lon1, lat2, lon2):
    """
    Berechnet die Entfernung zwischen zwei Punkten auf der Erde anhand der Haversine-Formel.
    Gibt die Distanz in Kilometern zurück.
    """
    R = 6371.0  # Erdradius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def stations_in_radius_view(request):
    """
    Gibt die nächstgelegenen Wetterstationen innerhalb eines Umkreises zurück.
    URL-Parameter: ?latitude=..., &longitude=..., &radius=..., &max_stations=...
    """
    try:
        lat = float(request.GET.get('latitude', 0))
        lon = float(request.GET.get('longitude', 0))
        radius_km = float(request.GET.get('radius', 10))
        max_stations = int(request.GET.get('max_stations', 10))
    except ValueError:
        return JsonResponse({"error": "Ungültige Parameter."}, status=400)

    # Liste mit Wetterstationen innerhalb des Radius
    nearest_stations = []
    for station in STATIONS:
        distance = haversine(lat, lon, station["latitude"], station["longitude"])
        if distance <= radius_km:
            nearest_stations.append({
                "station": station,
                "distance": distance
            })

    # Sortiere die Stationen nach Entfernung (aufsteigend) und beschränke auf max. Anzahl
    nearest_stations = sorted(nearest_stations, key=lambda x: x["distance"])[:max_stations]

    # JSON-Response mit der sortierten und begrenzten Liste zurückgeben
    response_data = [{
        "station_id": item["station"]["station_id"],
        "name": item["station"]["name"],
        "latitude": item["station"]["latitude"],
        "longitude": item["station"]["longitude"],
        "distance_km": round(item["distance"], 2)  # Rundet die Distanz für die Ausgabe
    } for item in nearest_stations]

    return JsonResponse(response_data, safe=False)
