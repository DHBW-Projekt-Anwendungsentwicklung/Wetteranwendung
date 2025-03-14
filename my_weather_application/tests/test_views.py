import os
import math
import io
import gzip
import csv
import json
from io import BytesIO, StringIO
from unittest import mock

from django.test import TestCase, Client
from django.urls import reverse
from django.http import JsonResponse

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

def mock_gzip_open_text(buffer):
        gzbin = gzip.GzipFile(fileobj=buffer, mode='rb')
        return io.TextIOWrapper(gzbin, encoding='utf-8')

class TestHaversine(TestCase):
    def test_haversine_same_point(self):
        distance = haversine(50.0, 9.0, 50.0, 9.0)
        self.assertEqual(distance, 0, "Distance should be 0 when points are identical.")

    def test_haversine_known_distance(self):
        distance = haversine(50.0, 0.0, 50.0, 1.0)
        self.assertTrue(60 < distance < 80, f"Expected distance near ~70, got {distance}")


class TestParseGhcnCsvGz(TestCase):
    
    def test_parse_valid_tmin_tmax(self):
        csv_content = """\
STATION,20200101,TMIN,50
STATION,20200101,TMAX,100
STATION,20200102,TMIN,40
STATION,20200102,PRCP,5
"""
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as gz:
            gz.write(csv_content.encode('utf-8'))
        buffer.seek(0)

        with mock.patch('gzip.open', return_value=mock_gzip_open_text(buffer)):
            records = parse_ghcn_csv_gz("dummy.csv.gz")
            self.assertEqual(len(records), 3, "PRCP sollte ignoriert werden, es bleiben TMIN/TMAX.")
            self.assertEqual(records[0]["element"], "TMIN")
            self.assertEqual(records[1]["element"], "TMAX")
            self.assertEqual(records[2]["element"], "TMIN")

    def test_parse_with_invalid_rows(self):
        csv_content = """\
STATION,20200101,TMIN,abc  # invalid float
STATION,2020bad,TMAX,100   # invalid date format
STATION,20200102,TMAX,100
"""
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as gzfile:
            gzfile.write(csv_content.encode('utf-8'))
        buffer.seek(0)

        with mock.patch('gzip.open', return_value=mock_gzip_open_text(buffer)):
            records = parse_ghcn_csv_gz("dummy.csv.gz")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["element"], "TMAX")
            self.assertEqual(records[0]["value"], 10.0)


class TestCalcYearlyStats(TestCase):
    def test_calc_yearly_stats_no_data(self):
        stats = calc_yearly_stats([], 2020, 2021, latitude=10)
        self.assertEqual(stats, [], "Keine Daten → leere Liste erwartet.")

    def test_calc_yearly_stats_partial_data_north(self):
        daily_records = [
            {"year": 2020, "month": 1, "day": 1, "element": "TMIN", "value": -5},
            {"year": 2020, "month": 1, "day": 1, "element": "TMAX", "value": 2},
            {"year": 2020, "month": 3, "day": 1, "element": "TMIN", "value": 5},
            {"year": 2021, "month": 12, "day": 31, "element": "TMAX", "value": 10},
        ]
        stats = calc_yearly_stats(daily_records, 2020, 2021, latitude=50)
        self.assertEqual(len(stats), 2, "Stats für 2020 und 2021 erwartet.")
        self.assertIn("yearly_min_mean", stats[0])
        self.assertIn("winter", stats[0])
        self.assertIn("winter", stats[1])

    def test_calc_yearly_stats_southern_hemisphere(self):
        daily_records = [
            {"year": 2019, "month": 12, "day": 15, "element": "TMIN", "value": 10},
            {"year": 2019, "month": 12, "day": 15, "element": "TMAX", "value": 25},
        ]
        stats = calc_yearly_stats(daily_records, 2020, 2020, latitude=-33.0)
        self.assertEqual(len(stats), 1)
        self.assertIn("summer", stats[0])
        self.assertIn("min:", stats[0]["summer"])
        self.assertIn("max:", stats[0]["summer"])


class TestDownloadCsvIfNeeded(TestCase):
    @mock.patch('os.path.isfile', return_value=True)
    def test_download_csv_if_needed_already_exists(self, mock_isfile):
        path = download_csv_if_needed("TESTSTATION")
        self.assertIn("TESTSTATION.csv.gz", path)

    @mock.patch('os.path.isfile', return_value=False)
    @mock.patch('requests.get')
    def test_download_csv_if_needed_download_ok(self, mock_req, mock_isfile):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = b'some binary data'
        mock_req.return_value = mock_response

        path = download_csv_if_needed("TESTSTATION2")
        self.assertIn("TESTSTATION2.csv.gz", path)

    @mock.patch('os.path.isfile', return_value=False)
    @mock.patch('requests.get')
    def test_download_csv_if_needed_download_empty(self, mock_req, mock_isfile):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = b''
        mock_req.return_value = mock_response

        path = download_csv_if_needed("EMPTYSTATION")
        self.assertIsNone(path, "Wenn kein Inhalt, sollte None zurückgegeben werden.")

    @mock.patch('os.path.isfile', return_value=False)
    @mock.patch('requests.get', side_effect=ConnectionError("No connection"))
    def test_download_csv_if_needed_download_fail(self, mock_requests_get, mock_os_path_isfile):
        with self.assertRaises(ConnectionError):
            download_csv_if_needed("FAILSTATION")


class TestViews(TestCase):

    def setUp(self):
        self.client = Client()

    def test_my_weather_application_view(self):
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
        url = reverse('stations_in_radius_view')
        response = self.client.get(url, {"latitude": "abc", "longitude": "xyz"})
        data = response.json()

        self.assertIn("Ungültige Parameter.", data["error"])
        self.assertEqual(response.status_code, 400)

    @mock.patch('my_weather_application.views.STATIONS', [
        {"station_id": "TEST1", "latitude": 10.0, "longitude": 10.0, "name": "FarAwayStation"},
    ])
    def test_stations_in_radius_view_no_stations_found(self):
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

    @mock.patch('my_weather_application.views.STATIONS', [
        {"station_id": "FAIL_CONNECTION", "latitude": 50.0, "longitude": 9.0, "name": "ConnTestStation"}
    ])
    @mock.patch('my_weather_application.views.download_csv_if_needed', side_effect=ConnectionError("Keine Verbindung"))
    def test_stations_in_radius_view_connection_error(self, mock_dl):
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
        mock_cache.get.return_value = None
        url = reverse('station_calculations_view')
        response = self.client.get(url, {"station_id": "TEST1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_station_calculations_view_no_station_id(self):
        url = reverse('station_calculations_view')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("No station_id provided", response.content.decode())

    @mock.patch('my_weather_application.views.STATIONS', [])
    def test_station_calculations_view_station_not_found(self):
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
        mock_cache.get.return_value = None
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
        self.assertIn("yearly_min_mean", data[0])
        self.assertIn("winter", data[0])
        mock_cache.set.assert_called()