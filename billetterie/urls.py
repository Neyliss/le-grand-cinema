from django.urls import path

from . import views

app_name = "billetterie"
urlpatterns = [
    path("<str:reference>/<str:jeton>/", views.billet, name="billet"),
    path("<str:reference>/<str:jeton>/pdf/", views.billet_pdf, name="billet_pdf"),
]
