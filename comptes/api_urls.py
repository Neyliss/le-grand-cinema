from django.urls import path

from . import api

urlpatterns = [
    path("", api.InscriptionAPI.as_view(), name="api_inscription"),
    path("confirmer/", api.ConfirmationAPI.as_view(), name="api_confirmer"),
    path("jeton/", api.JetonAPI.as_view(), name="api_jeton"),
    path("moi/", api.MonCompteAPI.as_view(), name="api_mon_compte"),
    path("moi/reservations/", api.MesReservationsAPI.as_view(), name="api_mes_reservations"),
]
