"""API publique de la programmation (lecture seule, sans compte) : les mêmes données que les pages
« Programmation » et « Plan de salle » (E1-US1, E2-US1), pour une future application mobile."""
from datetime import date

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from reservation.services import plan_de_salle

from .models import Film, Seance
from .views import avec_places_libres


class FilmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Film
        fields = ["id", "titre", "duree", "version", "classification", "festival", "synopsis", "affiche"]


class SeanceSerializer(serializers.ModelSerializer):
    film = serializers.CharField(source="film.titre")
    film_id = serializers.IntegerField()
    salle = serializers.CharField(source="salle.nom")
    fin = serializers.DateTimeField(read_only=True)
    places_libres = serializers.IntegerField(source="nb_libres")

    class Meta:
        model = Seance
        fields = ["id", "film_id", "film", "salle", "debut", "fin", "langue", "places_libres"]


@extend_schema(tags=["Programmation"], summary="Liste des films à l'affiche")
class FilmsAPI(generics.ListAPIView):
    authentication_classes = []  # lecture publique : aucun compte demandé
    serializer_class = FilmSerializer

    def get_queryset(self):
        return Film.objects.filter(seances__in=Seance.objects.a_venir()).distinct().order_by("titre")


@extend_schema(tags=["Programmation"], summary="Séances à venir, avec leurs places libres", parameters=[
    OpenApiParameter("jour", OpenApiTypes.DATE, description="Un jour précis, par exemple 2026-11-05"),
    OpenApiParameter("film", OpenApiTypes.INT, description="Le numéro d'un film"),
])
class SeancesAPI(generics.ListAPIView):
    authentication_classes = []  # lecture publique : aucun compte demandé
    serializer_class = SeanceSerializer

    def get_queryset(self):
        seances = Seance.objects.a_venir()
        if jour := self.request.query_params.get("jour"):
            try:
                seances = seances.du_jour(date.fromisoformat(jour))
            except ValueError:
                raise ValidationError({"jour": "Date attendue au format AAAA-MM-JJ."})
        if film := self.request.query_params.get("film"):
            if not film.isdigit():
                raise ValidationError({"film": "Numéro de film attendu."})
            seances = seances.filter(film_id=film)
        return avec_places_libres(seances).order_by("debut")


Plan = inline_serializer("PlanDeSalle", {
    "seance": serializers.IntegerField(), "reservable": serializers.BooleanField(),
    "allees": serializers.ListField(child=serializers.IntegerField()), "libres": serializers.IntegerField(),
    "rangees": serializers.ListField(child=serializers.DictField()), "maj": serializers.DateTimeField(),
})


@extend_schema(tags=["Programmation"], summary="Plan de salle d'une séance, en temps réel", responses={200: Plan},
               description="Chaque siège a un statut : libre, bloquee (en cours de paiement) ou vendue.")
class PlanAPI(generics.RetrieveAPIView):
    authentication_classes = []  # lecture publique : aucun compte demandé
    queryset = Seance.objects.filter(statut=Seance.Statut.PUBLIEE).select_related("salle")

    def retrieve(self, request, *args, **kwargs):
        return Response(plan_de_salle(self.get_object()))
