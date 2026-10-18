from django.urls import path

from . import views

app_name = "paiement"
urlpatterns = [
    path("<str:reference>/demonstration/", views.demo, name="demo"),
    path("<str:reference>/retour/", views.retour, name="retour"),
]
