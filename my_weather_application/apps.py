from django.apps import AppConfig


class MyWeatherApplicationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "my_weather_application"

# my_weather_application/apps.py

from django.apps import AppConfig

class MyWeatherApplicationConfig(AppConfig):
    name = 'my_weather_application'

    def ready(self):
        from . import station_data
        station_data.load_station_data()

