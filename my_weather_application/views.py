# my_weather_application/views.py

from django.shortcuts import render
import math
from django.http import JsonResponse
from .station_data import STATIONS

def my_weather_application(request):
    return render(request, 'frontend.html')

def haversine(lat1, lon1, lat2, lon2):
    """
    Berechnet die Entfernung zwischen zwei Punkten auf der Erde (Haversine-Formel).
    Gibt Distanz in Kilometern zurück.
    """
    R = 6371.0
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

    nearest_stations = []
    for station in STATIONS:
        distance = haversine(lat, lon, station["latitude"], station["longitude"])
        if distance <= radius_km:
            nearest_stations.append({
                "station": station,
                "distance": distance
            })

    nearest_stations = sorted(nearest_stations, key=lambda x: x["distance"])[:max_stations]

    # Nur station_id, name, latitude, longitude und distance_km
    response_data = []
    for item in nearest_stations:
        st = item["station"]
        response_data.append({
            "station_id": st["station_id"],
            "name":       st["name"],
            "latitude":   st["latitude"],
            "longitude":  st["longitude"],
            "distance_km": round(item["distance"], 2)
        })

    return JsonResponse(response_data, safe=False)
