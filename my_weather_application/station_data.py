import requests

STATIONS = []

def load_station_data():
    #Laden von Stationsdaten von NOAA; Extrahieren von Station-ID, Latitude, Longitude, Stationsname
    url = "https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"
    print(f"Lade Stationsdaten von {url} ...")

    response = requests.get(url)
    response.raise_for_status()

    lines = response.text.splitlines()
    parsed_stations = []
    for line in lines:
        if len(line) < 71:
            continue

        station_id = line[0:11].strip()
        lat = float(line[12:20].strip())
        lon = float(line[21:30].strip())
        name = line[41:71].strip() or None

        station_dict = {
            "station_id": station_id,
            "latitude":   lat,
            "longitude":  lon,
            "name":       name,
        }
        parsed_stations.append(station_dict)

    STATIONS.clear()
    STATIONS.extend(parsed_stations)
    print(f"Fertig. {len(STATIONS)} Stationen geladen.")
