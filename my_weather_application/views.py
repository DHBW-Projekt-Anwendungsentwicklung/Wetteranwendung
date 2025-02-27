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
    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def stations_in_radius_view(request):
    """
    Sucht nahe Wetterstationen im Umkreis (lat,lon,radius).
    """
    try:
        lat = float(request.GET.get('latitude', 0))
        lon = float(request.GET.get('longitude', 0))
        radius_km = float(request.GET.get('radius', 10))
        max_stations = int(request.GET.get('max_stations', 10))
    except ValueError:
        return JsonResponse({"error": "Ungültige Parameter."}, status=400)

    # Stationen filtern
    nearest_stations = []
    for station in STATIONS:
        distance = haversine(lat, lon, station["latitude"], station["longitude"])
        if distance <= radius_km:
            nearest_stations.append({
                "station": station,
                "distance": distance
            })

    # sortieren + begrenzen
    nearest_stations = sorted(nearest_stations, key=lambda x: x["distance"])[:max_stations]

    # JSON-Antwort
    response_data = []
    for item in nearest_stations:
        st = item["station"]
        response_data.append({
            "station_id": st["station_id"],
            "name": st["name"],
            "latitude": st["latitude"],
            "longitude": st["longitude"],
            "distance_km": round(item["distance"], 2)
        })
    return JsonResponse(response_data, safe=False)


# -----------------------------------------------------------
# CSV.GZ-Auswertung -> TMIN/TMAX => pro Jahr + Jahreszeiten
# -----------------------------------------------------------

def station_calculations_view(request):
    """
    Lädt CSV.GZ von NOAA by_station, parst TMIN/TMAX.
    Berechnet:
       - yearly_min_mean (Durchschnitt aller TMIN im Jahr)
       - yearly_max_mean (Durchschnitt aller TMAX im Jahr)
       - saisonale Min/Max (Winter, Frühling, Sommer, Herbst)
         -> Winter(Y) = Dez(Y-1) + Jan(Y) + Feb(Y)
    Gibt ein Array zurück mit:
       [
         {
           "year": 2020,
           "yearly_min_mean": "...",
           "spring": "...",
           ...
         },
         ...
       ]
    """
    station_id = request.GET.get('station_id')
    if not station_id:
        return JsonResponse({"error": "No station_id provided"}, status=400)

    try:
        year_from = int(request.GET.get('yearFrom', 1800))
        year_to = int(request.GET.get('yearTo', 2025))
    except ValueError:
        year_from = 1800
        year_to = 2025

    local_file = download_csv_if_needed(station_id)
    if not local_file:
        # Keine Daten => leeres Array
        return JsonResponse([], safe=False)

    # 1) Gesamte CSV parsen
    all_records = parse_ghcn_csv_gz(local_file)

    # 2) Filter: Wir nehmen ab (year_from - 1), damit der Dez des Vorjahres
    #    für das "erste" Jahr im Bereich verfügbar ist.
    #    Bis year_to reicht, um die Daten nicht unnötig zu vergrößern.
    daily_records = [
        r for r in all_records
        if (year_from - 1) <= r["year"] <= year_to
    ]

    # 3) Jahresstatistiken berechnen
    stats = calc_yearly_stats(daily_records, year_from, year_to)
    return JsonResponse(stats, safe=False)


def download_csv_if_needed(station_id):
    """
    Holt https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/by_station/{station_id}.csv.gz
    speichert es unter data_cache/{station_id}.csv.gz
    """
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
    except Exception as e:
        print(f"Fehler bei Download: {e}")
        return None


def parse_ghcn_csv_gz(filepath):
    """
    CSV.GZ: ID,DATE,ELEMENT,DATA VALUE,...
    TMIN/TMAX => value in Zehntel-Grad => /10
    Beispiel: "ACW00011604,20210101,TMAX,255,..."
      => year=2021, month=01, day=01, element="TMAX", value=25.5
    """
    records = []
    with gzip.open(filepath, "rt") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 4:
                continue
            station = row[0].strip()
            date_str = row[1].strip()  # YYYYMMDD
            element = row[2].strip()  # TMIN/TMAX
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


def calc_yearly_stats(daily_records, year_from, year_to):
    """
    Berechnet Jahres- und Jahreszeitenstatistiken für TMIN und TMAX.

    - yearly_min_mean: Durchschnitt aller TMIN pro Kalenderjahr (Jan-Dez)
    - yearly_max_mean: Durchschnitt aller TMAX pro Kalenderjahr (Jan-Dez)
    - Winter(Y) = Dez(Y-1), Jan(Y), Feb(Y)
    - Frühling: Mär, Apr, Mai
    - Sommer: Jun, Jul, Aug
    - Herbst: Sep, Okt, Nov

    Gibt Liste mit Dicts:
    [
      {
        "year": 2020,
        "yearly_min_mean": "...",
        "spring": "...",
        ...
      },
      ...
    ]
    zurück.
    """
    # Daten nach (year, month) bündeln
    data_by_year_month = defaultdict(lambda: {"TMIN": [], "TMAX": []})
    for r in daily_records:
        y, m = r["year"], r["month"]
        data_by_year_month[(y, m)][r["element"]].append(r["value"])

    results = []

    # Schleife über den gewünschten Jahresbereich (inklusive year_to)
    for year in range(year_from, year_to + 1):
        # 1) Jahresdurchschnittswerte (Jan-Dez)
        tmin_list = []
        tmax_list = []
        for m in range(1, 13):
            tmin_list.extend(data_by_year_month[(year, m)]["TMIN"])
            tmax_list.extend(data_by_year_month[(year, m)]["TMAX"])

        if tmin_list:
            yearly_min_mean = round(sum(tmin_list) / len(tmin_list), 1)
        else:
            yearly_min_mean = None

        if tmax_list:
            yearly_max_mean = round(sum(tmax_list) / len(tmax_list), 1)
        else:
            yearly_max_mean = None

        # Hilfsfunktion für min-/max-Text
        def build_temp_text(min_vals, max_vals):
            if min_vals and max_vals:
                return (f"min: {sum(min_vals) / len(min_vals):.1f}°C"
                        f"<br>max: {sum(max_vals) / len(max_vals):.1f}°C")
            else:
                return "Keine Daten"

        # Hilfsfunktion, die Werte für bestimmte (year,month)-Paare mittelt
        def gather_avg_for_pairs(pairs):
            tmp_min = []
            tmp_max = []
            for (yy, mm) in pairs:
                tmp_min.extend(data_by_year_month[(yy, mm)]["TMIN"])
                tmp_max.extend(data_by_year_month[(yy, mm)]["TMAX"])
            return build_temp_text(tmp_min, tmp_max)

        # 2) Jahreszeiten definieren
        # Winter(Y) = Dez(Y-1) + Jan(Y) + Feb(Y)
        # => wir rechnen immer (year-1,12), (year,1), (year,2) zusammen,
        #    damit auch das erste Jahr den Dezember des Vorjahres bekommt!
        winter_pairs = [
            (year - 1, 12),
            (year, 1),
            (year, 2),
        ]

        spring_pairs = [(year, 3), (year, 4), (year, 5)]
        summer_pairs = [(year, 6), (year, 7), (year, 8)]
        autumn_pairs = [(year, 9), (year, 10), (year, 11)]

        winter_str = gather_avg_for_pairs(winter_pairs)
        spring_str = gather_avg_for_pairs(spring_pairs)
        summer_str = gather_avg_for_pairs(summer_pairs)
        autumn_str = gather_avg_for_pairs(autumn_pairs)

        # 3) Ausgabe-Strings für das Jahr
        if yearly_min_mean is not None and yearly_max_mean is not None:
            yearly_str = f"min: {yearly_min_mean:.1f}°C<br>max: {yearly_max_mean:.1f}°C"
        else:
            yearly_str = "Keine Daten"

        results.append({
            "year": year,
            "yearly_min_mean": yearly_str,
            "spring": spring_str,
            "summer": summer_str,
            "autumn": autumn_str,
            "winter": winter_str,
        })

    return results
