from django.urls import path

from . import views

app_name = "guichet"
urlpatterns = [
    path("", views.tableau, name="tableau"),
    path("seance/<int:seance_id>/vendre/", views.vendre, name="vendre"),
    path("vente/<str:reference>/", views.imprimer, name="imprimer"),
]
