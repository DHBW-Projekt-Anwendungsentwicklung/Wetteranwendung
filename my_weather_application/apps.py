import sys
from django.apps import AppConfig

class MyWeatherApplicationConfig(AppConfig):
    #Laden von Stationsdaten bei Applikationsstart
    name = 'my_weather_application'
    
    def ready(self):
        if 'test' not in sys.argv:
            from . import station_data
            station_data.load_station_data()