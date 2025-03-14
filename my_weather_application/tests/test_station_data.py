import sys
import unittest
from unittest.mock import patch, Mock
from my_weather_application.station_data import load_station_data, STATIONS

class TestStationData(unittest.TestCase):

    def setUp(self):
        self._orig_argv = sys.argv.copy()
        sys.argv = [arg for arg in sys.argv if 'test' not in arg]
        STATIONS.clear()

    def tearDown(self):
        sys.argv = self._orig_argv

    @patch('my_weather_application.station_data.requests.get')
    def test_load_station_data_ok(self, mock_get):
        fake_text = """\
01234567890  50.1234   8.1234   123  XYZ SomeStation               .....
99999999999  55.0000  10.0000   567      AnotherStation           .....
SHORT
"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = fake_text
        mock_get.return_value = mock_response

        load_station_data()

        self.assertEqual(len(STATIONS), 2)

        self.assertEqual(STATIONS[0]['station_id'], '01234567890')
        self.assertAlmostEqual(STATIONS[0]['latitude'], 50.1234, places=4)
        self.assertAlmostEqual(STATIONS[0]['longitude'], 8.1234, places=4)
        self.assertEqual(STATIONS[0]['name'].rstrip(" ."), 'SomeStation')

        self.assertEqual(STATIONS[1]['station_id'], '99999999999')
        self.assertAlmostEqual(STATIONS[1]['latitude'], 55.0000, places=4)
        self.assertAlmostEqual(STATIONS[1]['longitude'], 10.0000, places=4)
        self.assertEqual(STATIONS[1]['name'].rstrip(" ."), 'AnotherStation')

    @patch('my_weather_application.station_data.requests.get')
    def test_load_station_data_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("HTTP Error 404")
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as ctx:
            load_station_data()
        self.assertIn("HTTP Error 404", str(ctx.exception))

    @patch('my_weather_application.station_data.requests.get')
    def test_load_station_data_empty(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_get.return_value = mock_response

        load_station_data()
        self.assertEqual(len(STATIONS), 0, "Es sollten keine Einträge geparst werden")

    @patch('my_weather_application.station_data.requests.get')
    def test_load_station_data_partial_line(self, mock_get):
        """
        Testet, ob eine Zeile < 71 Zeichen übersprungen wird.
        """
        fake_text = """\
012345678   49.0000   9.0000 SomeName (sehr kurz, < 71 Zeichen)
01234567890  49.1111   9.1111   111      ValidStation            ......
"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = fake_text
        mock_get.return_value = mock_response

        load_station_data()
        self.assertEqual(len(STATIONS), 1, "Nur eine Zeile ist lang genug, also nur 1 Station parsen")

        self.assertEqual(STATIONS[0]['station_id'], '01234567890')
        self.assertAlmostEqual(STATIONS[0]['latitude'], 49.1111, places=4)
        self.assertAlmostEqual(STATIONS[0]['longitude'], 9.1111, places=4)
        self.assertEqual(STATIONS[0]['name'].rstrip(" ."), 'ValidStation')


if __name__ == '__main__':
    unittest.main()