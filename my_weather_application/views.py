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

# 1) Distanzberechnung für die Stationssuche
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi/2)**2 +
         math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# 2) Stationssuche im Umkreis
def stations_in_radius_view(request):
    try:
        lat = float(request.GET.get('latitude', 0))
        lon = float(request.GET.get('longitude', 0))
        radius_km = float(request.GET.get('radius', 10))
        max_stations = int(request.GET.get('max_stations', 10))
    except ValueError:
        return JsonResponse({"error": "Ungültige Parameter."}, status=400)

    # Filter
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

# -----------------------------------------------------------
# NEU: CSV.GZ-Auswertung
# -----------------------------------------------------------

def station_calculations_view(request):
    """
    Lädt CSV.GZ (statt .dly) von NOAA by_station, parst TMIN/TMAX und gibt Jahresauswertungen zurück.
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
        # Keine Datei => leeres Array statt Fehler
        return JsonResponse([], safe=False)

    # CSV parsen
    daily_records = parse_ghcn_csv_gz(local_file)

    # Filter Zeitraum
    daily_records = [r for r in daily_records if year_from <= r["year"] <= year_to]

    # Jahresauswertung
    stats = calc_yearly_stats(daily_records)
    return JsonResponse(stats, safe=False)

def download_csv_if_needed(station_id):
    """
    Holt https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/by_station/{station_id}.csv.gz
    und speichert in data_cache/{station_id}.csv.gz
    Gibt Pfad zurück oder None, wenn Download fehlschlägt.
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
            print(f"Gecached: {local_path}")
            return local_path
        else:
            print(f"Keine Daten: HTTP {resp.status_code}, length={len(resp.content)}")
            return None
    except Exception as e:
        print(f"Fehler bei Download: {e}")
        return None

def parse_ghcn_csv_gz(filepath):
    """
    Liest CSV.GZ mit folgender Struktur:
    ID,DATE,ELEMENT,DATA VALUE,M-FLAG,Q-FLAG,S-FLAG,OBS-TIME
    z.B.:
    AEM00041194,19290101,PRCP,0,,,,
    AEM00041194,19290101,TMAX,278,,,,
    ...
    => extrahiert TMIN/TMAX => daily_records
    GHCN: T in Zehntel°C => also z.B. 278 => 27.8°C
    """
    records = []
    with gzip.open(filepath, "rt") as f:
        reader = csv.reader(f)
        for row in reader:
            # row: [station_id, date, element, value, m_flag, q_flag, s_flag, obs_time]
            if len(row) < 4:
                continue
            station = row[0].strip()
            date_str = row[1].strip()  # YYYYMMDD
            element = row[2].strip()   # TMIN, TMAX, ...
            val_str = row[3].strip()
            if not (element == "TMIN" or element == "TMAX"):
                # Wir interessieren uns nur für TMIN/TMAX
                continue

            # date_str => year,month,day
            if len(date_str) != 8:
                continue
            y = int(date_str[0:4])
            m = int(date_str[4:6])
            d = int(date_str[6:8])

            try:
                val = int(val_str)/10.0  # Zehntel °C -> °C
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
    daily_records => TMIN/TMAX
    => wir berechnen TAVG pro Tag => (TMIN+TMAX)/2
    => Jahresmittel => Saisons
    """
    data_by_year = defaultdict(list)
    for r in daily_records:
        data_by_year[r["year"]].append(r)

    results = []
    for year in sorted(data_by_year.keys()):
        entries = data_by_year[year]
        tmin_map = {}
        tmax_map = {}
        for e in entries:
            if e["element"] == "TMIN":
                tmin_map[(e["month"], e["day"])] = e["value"]
            elif e["element"] == "TMAX":
                tmax_map[(e["month"], e["day"])] = e["value"]

        daily_tavg = []
        spring_vals = []
        summer_vals = []
        autumn_vals = []
        winter_vals = []

        for (m,d), min_val in tmin_map.items():
            if (m,d) in tmax_map:
                max_val = tmax_map[(m,d)]
                tavg = (min_val + max_val)/2.0
                daily_tavg.append(tavg)

                # Saisons: 3..5, 6..8, 9..11, 12/1/2
                if m in [3,4,5]:
                    spring_vals.append(tavg)
                elif m in [6,7,8]:
                    summer_vals.append(tavg)
                elif m in [9,10,11]:
                    autumn_vals.append(tavg)
                else:
                    winter_vals.append(tavg)

        if daily_tavg:
            mean_year = sum(daily_tavg)/len(daily_tavg)
            def season_minmax(vals):
                return f"min:{min(vals):.1f}, max:{max(vals):.1f}" if vals else "Keine Daten"
            results.append({
                "year": year,
                "yearly_mean": round(mean_year,1),
                "spring": season_minmax(spring_vals),
                "summer": season_minmax(summer_vals),
                "autumn": season_minmax(autumn_vals),
                "winter": season_minmax(winter_vals),
            })
    return results
