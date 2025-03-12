import os
import math
import gzip
import csv
from io import BytesIO, StringIO
from unittest import mock

from django.test import TestCase, Client
from django.urls import reverse
from django.http import JsonResponse

# Importiere Funktionen und Variablen aus deinen Modulen
from my_weather_application.views import (
    my_weather_application,
    stations_in_radius_view,
    station_calculations_view,
    haversine,
    parse_ghcn_csv_gz,
    calc_yearly_stats,
    download_csv_if_needed,
)
from my_weather_application.station_data import STATIONS

class TestHaversine(TestCase):
    """Tests für die Hilfsfunktion 'haversine'."""
    def test_haversine_same_point(self):
        distance = haversine(50.0, 9.0, 50.0, 9.0)
        self.assertEqual(distance, 0, "Distance should be 0 when points are identical.")

    def test_haversine_known_distance(self):
        """
        Testet mit grob bekannten Koordinaten,
        z. B. (50,0) nach (50,1) ~ 70 km.
        """
        distance = haversine(50.0, 0.0, 50.0, 1.0)
        self.assertTrue(60 < distance < 80, f"Expected distance near ~70, got {distance}")


class TestParseGhcnCsvGz(TestCase):
    """Tests für parse_ghcn_csv_gz, welches CSV-GZ-Dateien liest und TMIN/TMAX erfasst."""
    def test_parse_valid_tmin_tmax(self):
        csv_content = """\
STATION,20200101,TMIN,50
STATION,20200101,TMAX,100
STATION,20200102,TMIN,40
STATION,20200102,PRCP,5
"""
        # Wir bauen eine GZIP-Datei in Memory
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as gzfile:
            gzfile.write(csv_content.encode('utf-8'))
        buffer.seek(0)

        with mock.patch('gzip.open', return_value=gzip.GzipFile(fileobj=buffer)) as mock_gz:
            records = parse_ghcn_csv_gz("dummy.csv.gz")
            self.assertEqual(len(records), 3, "PRCP sollte ignoriert werden, es bleiben TMIN/TMAX.")
            self.assertEqual(records[0]["element"], "TMIN")
            self.assertEqual(records[1]["element"], "TMAX")
            self.assertEqual(records[2]["element"], "TMIN")

    def test_parse_with_invalid_rows(self):
        """
        Testet, wie parse_ghcn_csv_gz auf leere oder fehlerhafte Zeilen reagiert.
        """
        csv_content = """\
STATION,20200101,TMIN,abc  # invalid float
STATION,2020bad,TMAX,100   # invalid date format
STATION,20200102,TMAX,100
"""
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as gzfile:
            gzfile.write(csv_content.encode('utf-8'))
        buffer.seek(0)

        with mock.patch('gzip.open', return_value=gzip.GzipFile(fileobj=buffer, mode='rt')):
            records = parse_ghcn_csv_gz("dummy.csv.gz")
            # Die erste Zeile hat 'abc' statt eines Werts → ValueError -> val=None -> ignoriert
            # Die zweite Zeile hat ein Dateiformat "2020bad" -> kein valider parse -> ignoriert
            # Nur die dritte Zeile ist gültig
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["element"], "TMAX")
            self.assertEqual(records[0]["value"], 10.0)  # 100/10.0


class TestCalcYearlyStats(TestCase):
    """Tests für calc_yearly_stats, das Jahres-/Saisonwerte aufbereitet."""
    def test_calc_yearly_stats_no_data(self):
        stats = calc_yearly_stats([], 2020, 2021, latitude=10)
        self.assertEqual(stats, [], "Keine Daten → leere Liste erwartet.")

    def test_calc_yearly_stats_partial_data_north(self):
        """
        Teilweise Daten für Nordhalbkugel, 
        damit wir 'winter', 'spring', etc. abdecken.
        """
        daily_records = [
            # Winter 2020
            {"year": 2020, "month": 1, "day": 1, "element": "TMIN", "value": -5},
            {"year": 2020, "month": 1, "day": 1, "element": "TMAX", "value": 2},
            # Frühjahr 2020
            {"year": 2020, "month": 3, "day": 1, "element": "TMIN", "value": 5},
            # 2021
            {"year": 2021, "month": 12, "day": 31, "element": "TMAX", "value": 10},
        ]
        stats = calc_yearly_stats(daily_records, 2020, 2021, latitude=50)
        self.assertEqual(len(stats), 2, "Stats für 2020 und 2021 erwartet.")
        # 2020: hat TMIN/TMAX in Jan + TMIN in März, TMAX in März fehlt
        self.assertIn("yearly_min_mean", stats[0])
        self.assertIn("winter", stats[0])
        # 2021: Nur TMAX am 31.12.
        self.assertIn("winter", stats[1])  # Da winter teils vom alten Jahr Dec + Jan + Feb

    def test_calc_yearly_stats_southern_hemisphere(self):
        """
        Prüft, ob der Code für latitude < 0 (Südhalbkugel) den Jahreszeiten-Shift richtig behandelt.
        """
        daily_records = [
            # Sommer auf Südhalbkugel (Dez, Jan, Feb), hier z.B. Dez 2020
            {"year": 2020, "month": 12, "day": 15, "element": "TMIN", "value": 10},
            {"year": 2020, "month": 12, "day": 15, "element": "TMAX", "value": 25},
        ]
        stats = calc_yearly_stats(daily_records, 2020, 2020, latitude=-33.0)
        self.assertEqual(len(stats), 1)
        # Wir prüfen, ob im Ergebnis "summer" mit unseren Werten gefüllt ist
        self.assertIn("summer", stats[0])
        self.assertIn("min:", stats[0]["summer"])
        self.assertIn("max:", stats[0]["summer"])


class TestDownloadCsvIfNeeded(TestCase):
    """Separater Test für download_csv_if_needed."""
    @mock.patch('os.path.isfile', return_value=True)
    def test_download_csv_if_needed_already_exists(self, mock_isfile):
        # Wenn die Datei bereits lokal existiert, wird kein erneuter Download durchgeführt
        path = download_csv_if_needed("TESTSTATION")
        self.assertIn("TESTSTATION.csv.gz", path)

    @mock.patch('os.path.isfile', return_value=False)
    @mock.patch('requests.get')
    def test_download_csv_if_needed_download_ok(self, mock_req, mock_isfile):
        """Mockt einen erfolgreichen Download."""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = b'some binary data'
        mock_req.return_value = mock_response

        path = download_csv_if_needed("TESTSTATION2")
        self.assertIn("TESTSTATION2.csv.gz", path)
        # Prüfen, ob die Datei geschrieben wurde (mock_open oder ähnliches)
        # Hier könnte man weiter verfeinern, z.B. ob open(..., "wb") aufgerufen wurde

    @mock.patch('os.path.isfile', return_value=False)
    @mock.patch('requests.get')
    def test_download_csv_if_needed_download_empty(self, mock_req, mock_isfile):
        """Mockt eine Antwort mit leerem Body - sollte None zurückliefern."""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = b''
        mock_req.return_value = mock_response

        path = download_csv_if_needed("EMPTYSTATION")
        self.assertIsNone(path, "Wenn kein Inhalt, sollte None zurückgegeben werden.")

    @mock.patch('os.path.isfile', return_value=False)
    @mock.patch('requests.get', side_effect=mock.Mock(side_effect=Exception("No connection")))
    def test_download_csv_if_needed_download_fail(self, mock_req, mock_isfile):
        """Simuliert einen ConnectionError."""
        with self.assertRaises(ConnectionError):
            download_csv_if_needed("FAILSTATION")


class TestViews(TestCase):
    """Integrationstests für die Views-Funktionen mittels Django TestClient."""

    def setUp(self):
        self.client = Client()

    def test_my_weather_application_view(self):
        """
        Testet, ob die Haupt-View (my_weather_application) ein Template zurückgibt.
        """
        # Wichtig: Du brauchst in urls.py einen Eintrag:
        # path('', my_weather_application, name='my_weather_application')
        url = reverse('my_weather_application')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'frontend.html')

    @mock.patch('my_weather_application.views.STATIONS', [
        {"station_id": "TEST1", "latitude": 50.0, "longitude": 9.0, "name": "Station1"},
        {"station_id": "TEST2", "latitude": 51.0, "longitude": 9.0, "name": "Station2"},
    ])
    @mock.patch('my_weather_application.views.download_csv_if_needed', return_value="dummy.csv.gz")
    @mock.patch('my_weather_application.views.parse_ghcn_csv_gz')
    def test_stations_in_radius_view_ok(self, mock_parse, mock_download):
        """
        Stationen innerhalb des Radius werden gefiltert und zurückgegeben,
        sofern yearFrom & yearTo Daten vorhanden sind.
        """
        mock_parse.return_value = [
            {"year": 1800, "element": "TMIN", "value": 1},
            {"year": 2025, "element": "TMAX", "value": 2},
        ]
        url = reverse('stations_in_radius_view')
        response = self.client.get(url, {
            "latitude": 50.0,
            "longitude": 9.0,
            "radius": 200,
            "max_stations": 5,
            "yearFrom": 1800,
            "yearTo": 2025
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2, "Sollte beide Stationen zurückgeben.")
        self.assertEqual(data[0]["station_id"], "TEST1")
        self.assertEqual(data[1]["station_id"], "TEST2")

    def test_stations_in_radius_view_invalid_params(self):
        """Ungültige Parameter sollen 400 liefern."""
        url = reverse('stations_in_radius_view')
        response = self.client.get(url, {"latitude": "abc", "longitude": "xyz"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Ungültige Parameter.", response.content.decode())

    @mock.patch('my_weather_application.views.STATIONS', [
        {"station_id": "TEST1", "latitude": 10.0, "longitude": 10.0, "name": "FarAwayStation"},
    ])
    def test_stations_in_radius_view_no_stations_found(self):
        """Station ist zu weit entfernt → 400 mit Fehlermeldung."""
        url = reverse('stations_in_radius_view')
        response = self.client.get(url, {
            "latitude": 50.0,
            "longitude": 9.0,
            "radius": 1,
            "yearFrom": 1900,
            "yearTo": 1950
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Keine Station im angegebenen Radius vorhanden", response.content.decode())

    @mock.patch('my_weather_application.views.download_csv_if_needed', side_effect=ConnectionError("Keine Verbindung"))
    def test_stations_in_radius_view_connection_error(self, mock_dl):
        """
        Simuliert, dass download_csv_if_needed eine ConnectionError wirft.
        View sollte dann 400 mit Meldung ausgeben.
        """
        url = reverse('stations_in_radius_view')
        response = self.client.get(url, {
            "latitude": 50.0,
            "longitude": 9.0,
            "radius": 50,
            "yearFrom": 2000,
            "yearTo": 2010
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Keine Verbindung zum Wetterdatenserver.", response.content.decode())

    @mock.patch('my_weather_application.views.STATIONS', [
        {"station_id": "TEST1", "latitude": 50.0, "longitude": 9.0, "name": "Test"},
    ])
    @mock.patch('my_weather_application.views.download_csv_if_needed', return_value=None)
    def test_stations_in_radius_view_file_none(self, mock_dl):
        """
        download_csv_if_needed gibt None zurück → keine Daten, 
        also keine valid_stations -> 400
        """
        url = reverse('stations_in_radius_view')
        response = self.client.get(url, {
            "latitude": 50.0,
            "longitude": 9.0,
            "radius": 100,
            "yearFrom": 2000,
            "yearTo": 2020
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Keine Station im angegebenen Radius vorhanden", response.content.decode())

    @mock.patch('my_weather_application.views.STATIONS', [
        {"station_id": "TEST1", "latitude": 50.0, "longitude": 9.0, "name": "MainStation"},
    ])
    @mock.patch('my_weather_application.views.cache')
    @mock.patch('my_weather_application.views.download_csv_if_needed', return_value="dummy.csv.gz")
    @mock.patch('my_weather_application.views.parse_ghcn_csv_gz', return_value=[])
    def test_station_calculations_view_no_data(self, mock_parse, mock_download, mock_cache):
        """
        Keine Datensätze -> Empty List, Status 200
        """
        mock_cache.get.return_value = None  # Cache-Miss
        url = reverse('station_calculations_view')
        response = self.client.get(url, {"station_id": "TEST1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_station_calculations_view_no_station_id(self):
        """Wenn station_id fehlt -> 400"""
        url = reverse('station_calculations_view')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("No station_id provided", response.content.decode())

    @mock.patch('my_weather_application.views.STATIONS', [])
    def test_station_calculations_view_station_not_found(self):
        """Station existiert nicht -> 404"""
        url = reverse('station_calculations_view')
        response = self.client.get(url, {"station_id": "UNKNOWN"})
        self.assertEqual(response.status_code, 404)
        self.assertIn("Station not found", response.content.decode())

    @mock.patch('my_weather_application.views.STATIONS', [
        {"station_id": "TEST1", "latitude": -23.0, "longitude": 133.0, "name": "SüdhalbkugelStation"},
    ])
    @mock.patch('my_weather_application.views.cache')
    @mock.patch('my_weather_application.views.download_csv_if_needed', return_value="dummy.csv.gz")
    @mock.patch('my_weather_application.views.parse_ghcn_csv_gz')
    def test_station_calculations_view_data_ok(self, mock_parse, mock_download, mock_cache):
        """Station auf Südhalbkugel, Datensätze vorhanden."""
        mock_cache.get.return_value = None  # Cache-Miss
        mock_parse.return_value = [
            {"year": 2020, "month": 6, "day": 15, "element": "TMIN", "value": 5},
            {"year": 2020, "month": 6, "day": 15, "element": "TMAX", "value": 15},
        ]
        url = reverse('station_calculations_view')
        response = self.client.get(url, {"station_id": "TEST1"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(isinstance(data, list))
        self.assertEqual(data[0]["year"], 2020)
        # Prüfe, ob die Felder existieren
        self.assertIn("yearly_min_mean", data[0])
        self.assertIn("winter", data[0])  # Im Südhalbkugel-Case = Juni/Juli/Aug
        mock_cache.set.assert_called()  # Daten werden in den Cache geschrieben