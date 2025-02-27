# my_weather_application/urls.py

from django.urls import path
from .views import (
    my_weather_application,
    stations_in_radius_view,
    station_calculations_view,
)

urlpatterns = [
    # Dein Frontend-Start
    path('', my_weather_application, name='my_weather_application'),

    # Radius-Suche
    path('stations/in_radius/', stations_in_radius_view, name='stations_in_radius'),

    # Die neue Route für die Auswertungen (Jahres-Mittelwerte etc.)
    path('station_calculations/', station_calculations_view, name='station_calculations'),
]
