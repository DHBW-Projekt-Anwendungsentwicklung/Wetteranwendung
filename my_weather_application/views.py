from django.shortcuts import render


def my_weather_application(request):
    return render(request, 'frontend.html')


# my_weather_application/views.py

import math
from django.http import JsonResponse
from .station_data import STATIONS


def stations_in_radius_view(request):
    """
    Beispiel-View, das Stationen innerhalb eines Umkreises zurückgibt.
    URL-Parameter: ?latitude=..., &longitude=..., &radius=..., &max_stations=...
    """
    try:
        lat = float(request.GET.get('latitude', 0))
        lon = float(request.GET.get('longitude', 0))
        radius_km = float(request.GET.get('radius', 10))
        max_stations = int(request.GET.get('max_stations', 10))
    except ValueError:
        return JsonResponse({"error": "Ungültige Parameter."}, status=400)

    R = 6371.0  # Erdradius (km)
    result = []
    for station in STATIONS:
        d_lat = math.radians(station["latitude"] - lat)
        d_lon = math.radians(station["longitude"] - lon)
        a = (math.sin(d_lat/2)**2 +
             math.cos(math.radians(lat)) * math.cos(math.radians(station["latitude"])) * math.sin(d_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        dist = R * c

        if dist <= radius_km:
            result.append(station)

    # Nur max. Anzahl ausgeben
    result = result[:max_stations]

    return JsonResponse(result, safe=False)
