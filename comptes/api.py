"""API du compte spectateur (E9-US1). Elle applique exactement les mêmes règles que les pages
du site : tout passe par comptes/services.py."""
from django.contrib.auth import authenticate, password_validation
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import (CompteExistant, confirmer, creer_compte, est_spectateur_confirme, normaliser,
                       reservations_du_compte, supprimer_compte)


class InscriptionSerializer(serializers.Serializer):
    nom = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    mot_de_passe = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_email(self, valeur):
        return normaliser(valeur)

    def validate_mot_de_passe(self, valeur):
        password_validation.validate_password(valeur)
        return valeur


class ConnexionSerializer(serializers.Serializer):
    email = serializers.EmailField()
    mot_de_passe = serializers.CharField(write_only=True, style={"input_type": "password"})


class ConfirmationSerializer(serializers.Serializer):
    jeton = serializers.CharField(help_text="Le code présent à la fin du lien reçu par e-mail.")


class CompteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    nom = serializers.CharField(source="first_name")
    email_confirme = serializers.BooleanField(source="profil.email_confirme")


class ReservationSerializer(serializers.Serializer):
    reference = serializers.CharField()
    film = serializers.CharField(source="seance.film.titre")
    debut = serializers.DateTimeField(source="seance.debut")
    salle = serializers.CharField(source="seance.salle.nom")
    statut = serializers.CharField()
    nombre_de_places = serializers.IntegerField(source="places.count")


Message = inline_serializer("Message", {"detail": serializers.CharField()})
Jeton = inline_serializer("Jeton", {"jeton": serializers.CharField()})


class InscriptionAPI(APIView):
    authentication_classes = []  # route publique : pas besoin d'être connecté
    throttle_scope = "comptes"

    @extend_schema(tags=["Compte spectateur"], summary="Créer un compte", request=InscriptionSerializer,
                   responses={201: Message, 400: Message, 409: Message},
                   description="Le compte est créé non confirmé : un lien de confirmation part par e-mail.")
    def post(self, request):
        donnees = InscriptionSerializer(data=request.data)
        donnees.is_valid(raise_exception=True)
        try:
            creer_compte(donnees.validated_data["email"], donnees.validated_data["mot_de_passe"], donnees.validated_data["nom"])
        except CompteExistant:
            return Response({"detail": "Un compte existe déjà avec cette adresse."}, status=status.HTTP_409_CONFLICT)
        return Response({"detail": "Compte créé : confirmez l'adresse avec le lien reçu par e-mail."},
                        status=status.HTTP_201_CREATED)


class ConfirmationAPI(APIView):
    authentication_classes = []  # route publique : pas besoin d'être connecté
    throttle_scope = "comptes"

    @extend_schema(tags=["Compte spectateur"], summary="Confirmer l'adresse e-mail", request=ConfirmationSerializer,
                   responses={200: Message, 400: Message},
                   description="Les réservations déjà faites avec cette adresse sont rattachées au compte.")
    def post(self, request):
        donnees = ConfirmationSerializer(data=request.data)
        donnees.is_valid(raise_exception=True)
        if confirmer(donnees.validated_data["jeton"]) is None:
            return Response({"detail": "Lien de confirmation faux ou trop ancien."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Adresse confirmée."})


class JetonAPI(APIView):
    authentication_classes = []  # route publique : pas besoin d'être connecté
    throttle_scope = "comptes"

    @extend_schema(tags=["Compte spectateur"], summary="Se connecter (obtenir un jeton)", request=ConnexionSerializer,
                   responses={200: Jeton, 400: Message},
                   description="Renvoie le jeton à placer ensuite dans l'en-tête « Authorization: Token <jeton> ».")
    def post(self, request):
        donnees = ConnexionSerializer(data=request.data)
        donnees.is_valid(raise_exception=True)
        utilisateur = authenticate(request, username=normaliser(donnees.validated_data["email"]),
                                   password=donnees.validated_data["mot_de_passe"])
        if utilisateur is None or not est_spectateur_confirme(utilisateur):
            # Même réponse dans les deux cas : on ne révèle pas si l'adresse a un compte.
            return Response({"detail": "Identifiants incorrects ou adresse non confirmée."}, status=status.HTTP_400_BAD_REQUEST)
        jeton, _ = Token.objects.get_or_create(user=utilisateur)
        return Response({"jeton": jeton.key})


class MonCompteAPI(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Compte spectateur"], summary="Voir mon compte", responses={200: CompteSerializer, 401: Message})
    def get(self, request):
        return Response(CompteSerializer(request.user).data)

    @extend_schema(tags=["Compte spectateur"], summary="Supprimer mon compte (RGPD)", responses={204: None, 401: Message},
                   description="Supprime le compte, le nom et l'adresse e-mail. Les billets achetés restent valables.")
    def delete(self, request):
        supprimer_compte(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MesReservationsAPI(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Compte spectateur"], summary="Mes réservations", responses={200: ReservationSerializer(many=True), 401: Message})
    def get(self, request):
        reservations = reservations_du_compte(request.user).prefetch_related("places")
        return Response(ReservationSerializer(reservations, many=True).data)
