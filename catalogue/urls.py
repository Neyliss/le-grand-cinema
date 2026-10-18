from django.urls import path

from . import views

app_name = "catalogue"
urlpatterns = [
    path("", views.programmation, name="programmation"),
    path("festival/", views.festival, name="festival"),
    path("infos/", views.infos, name="infos"),
]
