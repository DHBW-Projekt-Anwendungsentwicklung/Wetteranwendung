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
            "name":       st["name"],
            "latitude":   st["latitude"],
            "longitude":  st["longitude"],
            "distance_km": round(item["distance"], 2)
        })
    return JsonResponse(response_data, safe=False)

# -----------------------------------------------------------
# NEU: CSV.GZ-Auswertung -> TMIN/TMAX => pro Jahr + Jahreszeiten
# -----------------------------------------------------------

def station_calculations_view(request):
    """
    Lädt CSV.GZ von NOAA by_station, parst TMIN/TMAX.
    Berechnet:
       - yearly_min_mean (Durchschnitt aller TMIN im Jahr)
       - yearly_max_mean (Durchschnitt aller TMAX im Jahr)
       - min/max pro Jahreszeit basierend auf Tagesmittel (TAVG=(TMIN+TMAX)/2)
    Gibt array mit {year, yearly_min_mean, yearly_max_mean, spring, summer, autumn, winter}.
    """
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
        # Keine Daten => leeres Array
        return JsonResponse([], safe=False)

    # CSV parsen
    daily_records = parse_ghcn_csv_gz(local_file)

    # Jahr-Filter
    daily_records = [r for r in daily_records if year_from <= r["year"] <= year_to]

    # Jahresauswertung
    stats = calc_yearly_stats(daily_records)
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
    z.B. "ACW00011604,20210101,TMAX,255,..."
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
            element  = row[2].strip()  # TMIN/TMAX
            val_str  = row[3].strip()

            if not (element == "TMIN" or element == "TMAX"):
                continue
            if len(date_str) != 8:
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
    """
    Berechnet:
      - yearly_min_mean = Durchschnitt aller TMIN pro Jahr
      - yearly_max_mean = Durchschnitt aller TMAX pro Jahr
      - saisonale min/max auf Basis der Durchschnittswerte der TMIN und TMAX
    """
    data_by_year = defaultdict(list)
    for r in daily_records:
        data_by_year[r["year"]].append(r)

    results = []
    for year in sorted(data_by_year.keys()):
        entries = data_by_year[year]

        # 1) Sammeln TMIN/TMAX
        tmin_list = []
        tmax_list = []

        # 2) Speichern TMIN und TMAX getrennt für Jahreszeiten
        spring_tmin = []
        spring_tmax = []
        summer_tmin = []
        summer_tmax = []
        autumn_tmin = []
        autumn_tmax = []
        winter_tmin = []
        winter_tmax = []

        for e in entries:
            if e["element"] == "TMIN":
                tmin_list.append(e["value"])

                # Sortierung nach Jahreszeiten für TMIN
                if e["month"] in [3, 4, 5]:
                    spring_tmin.append(e["value"])
                elif e["month"] in [6, 7, 8]:
                    summer_tmin.append(e["value"])
                elif e["month"] in [9, 10, 11]:
                    autumn_tmin.append(e["value"])
                else:
                    winter_tmin.append(e["value"])

            elif e["element"] == "TMAX":
                tmax_list.append(e["value"])

                # Sortierung nach Jahreszeiten für TMAX
                if e["month"] in [3, 4, 5]:
                    spring_tmax.append(e["value"])
                elif e["month"] in [6, 7, 8]:
                    summer_tmax.append(e["value"])
                elif e["month"] in [9, 10, 11]:
                    autumn_tmax.append(e["value"])
                else:
                    winter_tmax.append(e["value"])

        # Jahres-Durchschnitte
        yearly_min_mean = round(sum(tmin_list)/len(tmin_list), 1) if tmin_list else None
        yearly_max_mean = round(sum(tmax_list)/len(tmax_list), 1) if tmax_list else None

        # Funktion zum Berechnen von min/max für eine Jahreszeit
        def season_avg(vals_min, vals_max):
            if vals_min and vals_max:
                return f"min: {sum(vals_min)/len(vals_min):.1f}°C<br>max: {sum(vals_max)/len(vals_max):.1f}°C"
            return "Keine Daten"

        results.append({
            "year": year,
            "yearly_min_mean": f"min: {yearly_min_mean:.1f}°C<br>max: {yearly_max_mean:.1f}°C" if yearly_min_mean is not None and yearly_max_mean is not None else "Keine Daten",
            "spring": season_avg(spring_tmin, spring_tmax),
            "summer": season_avg(summer_tmin, summer_tmax),
            "autumn": season_avg(autumn_tmin, autumn_tmax),
            "winter": season_avg(winter_tmin, winter_tmax),
        })
    return results
