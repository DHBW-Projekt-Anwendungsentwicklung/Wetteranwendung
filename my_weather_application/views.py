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
from django.core.cache import cache

def my_weather_application(request):
    logger.info("my_weather_application wurde aufgerufen")
    return render(request, 'frontend.html')

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def stations_in_radius_view(request):
    try:
        lat = float(request.GET.get('latitude', 0))
        lon = float(request.GET.get('longitude', 0))
        radius_km = float(request.GET.get('radius', 10))
        max_stations = int(request.GET.get('max_stations', 10))
        year_from = int(request.GET.get('yearFrom', 1800))
        year_to = int(request.GET.get('yearTo', 2025))
    except ValueError:
        return JsonResponse({"error": "Ungültige Parameter."}, status=400)

    def has_valid_data_for_year(station_id, year):
        local_file = download_csv_if_needed(station_id)
        if local_file is None:
            return False
        records = parse_ghcn_csv_gz(local_file)
        return any(r for r in records if r["year"] == year and r["element"] in ("TMIN", "TMAX"))

    # Zunächst alle Stationen innerhalb des Radius sammeln und nach Entfernung sortieren
    candidate_stations = []
    for station in STATIONS:
        distance = haversine(lat, lon, station["latitude"], station["longitude"])
        if distance <= radius_km:
            candidate_stations.append({
                "station": station,
                "distance": distance
            })

    candidate_stations = sorted(candidate_stations, key=lambda x: x["distance"])

    # Nun die sortierte Liste durchgehen und nur die Stationen mit gültigen Daten auswählen
    valid_stations = []
    try:
        for candidate in candidate_stations:
            station = candidate["station"]
            if (has_valid_data_for_year(station["station_id"], year_from) and
                has_valid_data_for_year(station["station_id"], year_to)):
                valid_stations.append(candidate)
                if len(valid_stations) >= max_stations:
                    break
    except ConnectionError:
        return JsonResponse({"error": "Keine Verbindung zum Wetterdatenserver."}, status=400)

    if not valid_stations:
        return JsonResponse({"error": "Keine Station im angegebenen Radius vorhanden."}, status=400)

    response_data = []
    for item in valid_stations:
        st = item["station"]
        response_data.append({
            "station_id": st["station_id"],
            "name": st["name"],
            "latitude": st["latitude"],
            "longitude": st["longitude"],
            "distance_km": round(item["distance"], 2)
        })
    return JsonResponse(response_data, safe=False)



def station_calculations_view(request):
    station_id = request.GET.get('station_id')
    if not station_id:
        return JsonResponse({"error": "No station_id provided"}, status=400)

    cache_key = f"station_data_{station_id}"
    cached_data = cache.get(cache_key)

    if cached_data:
        print(f"Cache-Hit für Station {station_id}")
        return JsonResponse(cached_data, safe=False)

    print(f"Cache-Miss für Station {station_id}, Daten werden geladen...")

    station = next((s for s in STATIONS if s["station_id"] == station_id), None)
    if station is None:
        return JsonResponse({"error": "Station not found"}, status=404)

    station_lat = station["latitude"]

    try:
        year_from = int(request.GET.get('yearFrom', 1800))
        year_to = int(request.GET.get('yearTo', 2025))
    except ValueError:
        year_from = 1800
        year_to = 2025

    local_file = download_csv_if_needed(station_id)

    all_records = parse_ghcn_csv_gz(local_file)
    daily_records = [r for r in all_records if (year_from - 1) <= r["year"] <= year_to]

    stats = calc_yearly_stats(daily_records, year_from, year_to, station_lat)

    if not stats:
        return JsonResponse([], safe=False)

    cache.set(cache_key, stats, timeout=600)

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
            print(f"Gespeichert: {local_path}")
            return local_path
        else:
            print(f"Keine Daten: HTTP {resp.status_code}, length={len(resp.content)}")
            return None
    except requests.exceptions.ConnectionError:
        print("Fehler: Keine Verbindung zum Wetterdatenserver.")
        raise ConnectionError("Keine Verbindung zum Wetterdatenserver.")

def parse_ghcn_csv_gz(filepath):
    records = []
    with gzip.open(filepath, "rt") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 4:
                continue
            station = row[0].strip()
            date_str = row[1].strip()  # YYYYMMDD
            element = row[2].strip()   # TMIN/TMAX
            val_str = row[3].strip()

            if element not in ("TMIN", "TMAX"):
                continue
            if len(date_str) != 8:
                continue

            y = int(date_str[0:4])
            m = int(date_str[4:6])
            d = int(date_str[6:8])

            try:
                val = int(val_str) / 10.0
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

def calc_yearly_stats(daily_records, year_from, year_to, latitude):
    data_by_year_month = defaultdict(lambda: {"TMIN": [], "TMAX": []})
    for r in daily_records:
        y, m = r["year"], r["month"]
        data_by_year_month[(y, m)][r["element"]].append(r["value"])

    available_years = sorted(set(y for y, _ in data_by_year_month.keys()))
    if not available_years:
        return []

    first_available_year = max(min(available_years), year_from)

    results = []

    def build_temp_text(min_vals, max_vals, missing=False):
        if missing:
            return "Keine Daten"
        if min_vals and max_vals:
            return (f"min: {sum(min_vals) / len(min_vals):.1f}°C"
                    f"<br>max: {sum(max_vals) / len(max_vals):.1f}°C")
        else:
            return "Keine Daten"

    def gather_avg_for_pairs(pairs):
        tmp_min = []
        tmp_max = []
        missing = all((yy, mm) not in data_by_year_month for yy, mm in pairs)

        for (yy, mm) in pairs:
            tmp_min.extend(data_by_year_month[(yy, mm)]["TMIN"])
            tmp_max.extend(data_by_year_month[(yy, mm)]["TMAX"])
        return build_temp_text(tmp_min, tmp_max, missing)

    for year in range(first_available_year, year_to + 1):
        # Alle TMIN/TMAX-Werte für dieses Jahr sammeln
        tmin_list = []
        tmax_list = []
        for m in range(1, 13):
            if (year, m) in data_by_year_month:
                tmin_list.extend(data_by_year_month[(year, m)]["TMIN"])
                tmax_list.extend(data_by_year_month[(year, m)]["TMAX"])

        # Jahresmittel für TMIN / TMAX
        def average_or_none(values):
            return round(sum(values) / len(values), 1) if values else None

        yearly_min_mean = average_or_none(tmin_list)
        yearly_max_mean = average_or_none(tmax_list)

        if latitude < 0:
            # Südhalbkugel
            summer_pairs = [(year - 1, 12), (year, 1), (year, 2)]
            autumn_pairs = [(year, 3), (year, 4), (year, 5)]
            winter_pairs = [(year, 6), (year, 7), (year, 8)]
            spring_pairs = [(year, 9), (year, 10), (year, 11)]
        else:
            # Nordhalbkugel
            winter_pairs = [(year - 1, 12), (year, 1), (year, 2)]
            spring_pairs = [(year, 3), (year, 4), (year, 5)]
            summer_pairs = [(year, 6), (year, 7), (year, 8)]
            autumn_pairs = [(year, 9), (year, 10), (year, 11)]

        winter_str = gather_avg_for_pairs(winter_pairs)
        spring_str = gather_avg_for_pairs(spring_pairs)
        summer_str = gather_avg_for_pairs(summer_pairs)
        autumn_str = gather_avg_for_pairs(autumn_pairs)

        if not tmin_list and not tmax_list:
            yearly_str = "Keine Daten"
        else:
            yearly_str = (f"min: {yearly_min_mean}°C<br>"
                          f"max: {yearly_max_mean}°C")

        results.append({
            "year": year,
            "yearly_min_mean": yearly_str,
            "spring": spring_str,
            "summer": summer_str,
            "autumn": autumn_str,
            "winter": winter_str,
        })

    return results
