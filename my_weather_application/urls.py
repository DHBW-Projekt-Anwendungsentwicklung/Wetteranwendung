from django.urls import path
from . import views
from .views import my_weather_application, stations_in_radius_view

urlpatterns = [
    path('', my_weather_application, name='my_weather_application'),
    path('stations/in_radius/', stations_in_radius_view, name='stations_in_radius'),
]
