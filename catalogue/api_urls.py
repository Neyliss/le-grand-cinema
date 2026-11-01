from django.urls import path

from . import api

urlpatterns = [
    path("films/", api.FilmsAPI.as_view(), name="api_films"),
    path("seances/", api.SeancesAPI.as_view(), name="api_seances"),
    path("seances/<int:pk>/plan/", api.PlanAPI.as_view(), name="api_plan"),
]
