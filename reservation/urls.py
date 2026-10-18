from django.urls import path

from . import views

app_name = "reservation"
urlpatterns = [
    path("seance/<int:seance_id>/", views.plan, name="plan"),
    path("seance/<int:seance_id>/plan.json", views.api_plan, name="api_plan"),
    path("seance/<int:seance_id>/bloquer/", views.bloquer, name="bloquer"),
    path("<str:reference>/", views.recapitulatif, name="recapitulatif"),
]
