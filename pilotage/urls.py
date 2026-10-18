from django.urls import path

from . import views

app_name = "pilotage"
urlpatterns = [
    path("", views.tableau, name="tableau"),
    path("export.csv", views.export_csv, name="export_csv"),
]
