from django.urls import path
from . import views

urlpatterns = [
    path('my_weather_application/', views.my_weather_application, name='my_weather_application'),
]
