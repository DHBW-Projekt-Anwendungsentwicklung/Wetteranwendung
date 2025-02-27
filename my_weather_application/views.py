# my_weather_application/views.py

from django.shortcuts import render
import math
from django.http import JsonResponse
from .station_data import STATIONS
import os
import requests
import gzip
import csv
from collections import defaultdict

def my_weather_application(request):
    return render(request, 'frontend.html')

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi/2)**2 +
         math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def stations_in_radius_view(request):
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

# --------------------------------------
# CSV.GZ-Auswertung -> TMIN/TMAX Jahreszeiten
# --------------------------------------

def station_calculations_view(request):
    station_id = request.GET.get('station_id')
    if not station_id:
        return JsonResponse({"error": "No station_id provided"}, status=400)

    try:
        year_from = int(request.GET.get('yearFrom', 1800))
        year_to   = int(request.GET.get('yearTo', 2025))
    except ValueError:
        year_from = 1800
        year_to   = 2025

    local_file = download_csv_if_needed(station_id)
    if not local_file:
        return JsonResponse([], safe=False)

    daily_records = parse_ghcn_csv_gz(local_file)
    daily_records = [r for r in daily_records if year_from <= r["year"] <= year_to]

    stats = calc_yearly_stats(daily_records)
    return JsonResponse(stats, safe=False)

def download_csv_if_needed(station_id):
    cache_dir = os.path.join(os.path.dirname(__file__), "data_cache")
    os.makedirs(cache_dir, exist_ok=True)

    local_path = os.path.join(cache_dir, f"{station_id}.csv.gz")
    if os.path.isfile(local_path):
        return local_path

    base_url = "https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/by_station"
    url = f"{base_url}/{station_id}.csv.gz"
    print(f"Downloading {url}...")

    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200 and len(resp.content) > 0:
            with open(local_path, "wb") as f:
                f.write(resp.content)
            return local_path
        else:
            return None
    except Exception as e:
        print(f"Fehler bei Download: {e}")
        return None

def parse_ghcn_csv_gz(filepath):
    records = []
    with gzip.open(filepath, "rt") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 4:
                continue
            station = row[0].strip()
            date_str = row[1].strip()
            element  = row[2].strip()
            val_str  = row[3].strip()

            if element not in ["TMIN", "TMAX"] or len(date_str) != 8:
                continue

            y = int(date_str[0:4])
            m = int(date_str[4:6])
            d = int(date_str[6:8])

            try:
                val = int(val_str)/10.0
            except ValueError:
                val = None

            if val is not None:
                records.append({
                    "station_id": station,
                    "year": y,
                    "month": m,
                    "day": d,
                    "element": element,
                    "value": val
                })
    return records

def calc_yearly_stats(daily_records):
    data_by_year = defaultdict(list)
    for r in daily_records:
        data_by_year[r["year"]].append(r)

    results = []
    for year in sorted(data_by_year.keys()):
        entries = data_by_year[year]

        tmin_list = []
        tmax_list = []

        seasons = {"spring": [], "summer": [], "autumn": [], "winter": []}

        for e in entries:
            if e["element"] == "TMIN":
                tmin_list.append(e["value"])
            elif e["element"] == "TMAX":
                tmax_list.append(e["value"])

            season_key = "winter" if e["month"] in [12,1,2] else \
                         "spring" if e["month"] in [3,4,5] else \
                         "summer" if e["month"] in [6,7,8] else "autumn"
            seasons[season_key].append(e["value"])

        def season_avg(values):
            return f"min: {min(values):.1f}°C<br>max: {max(values):.1f}°C" if values else "Keine Daten"

        results.append({
            "year": year,
            "yearly_min_mean": f"min: {sum(tmin_list)/len(tmin_list):.1f}°C<br>max: {sum(tmax_list)/len(tmax_list):.1f}°C" if tmin_list and tmax_list else "Keine Daten",
            "spring": season_avg(seasons["spring"]),
            "summer": season_avg(seasons["summer"]),
            "autumn": season_avg(seasons["autumn"]),
            "winter": season_avg(seasons["winter"]),
        })
    return results
