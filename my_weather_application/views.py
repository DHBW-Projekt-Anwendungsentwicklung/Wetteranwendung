from django.shortcuts import render


def my_weather_application(request):
    return render(request, 'frontend.html')
