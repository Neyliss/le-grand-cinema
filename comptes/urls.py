from django.urls import path

from . import views

app_name = "comptes"
urlpatterns = [
    path("creer/", views.inscription, name="inscription"),
    path("confirmer/<str:jeton>/", views.confirmation, name="confirmer"),
    path("connexion/", views.connexion, name="connexion"),
    path("deconnexion/", views.deconnexion, name="deconnexion"),
    path("", views.mon_compte, name="mon_compte"),
    path("supprimer/", views.suppression, name="supprimer"),
    path("preferences/", views.preferences, name="preferences"),
]
