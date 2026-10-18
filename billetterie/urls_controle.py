from django.urls import path

from . import views

app_name = "controle"
urlpatterns = [
    path("", views.controle_seances, name="seances"),
    path("seance/<int:seance_id>/", views.controle, name="scanner"),
    path("seance/<int:seance_id>/verifier/", views.controle_verifier, name="verifier"),
]
