"""Règles du compte spectateur (E9-US1), utilisées à l'identique par les pages du site et par l'API."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import translation

from reservation.models import Reservation

from .models import Profil

GROUPE_SPECTATEURS = "Spectateurs"
SEL_CONFIRMATION = "comptes.confirmation"
DUREE_LIEN_CONFIRMATION = 3 * 24 * 3600  # le lien de confirmation reste valable 3 jours


class CompteExistant(Exception):
    """Un compte existe déjà avec cette adresse e-mail."""


def normaliser(email):
    return email.strip().lower()


@transaction.atomic
def creer_compte(email, mot_de_passe, nom=""):
    """Crée le compte (non confirmé) puis envoie le lien de confirmation par e-mail."""
    email = normaliser(email)
    Utilisateur = get_user_model()
    if Utilisateur.objects.filter(username=email).exists():
        raise CompteExistant()
    utilisateur = Utilisateur.objects.create_user(username=email, email=email, password=mot_de_passe, first_name=nom[:150])
    Profil.objects.create(utilisateur=utilisateur)
    utilisateur.groups.add(Group.objects.get_or_create(name=GROUPE_SPECTATEURS)[0])
    transaction.on_commit(lambda: envoyer_confirmation(utilisateur))
    return utilisateur


def jeton_confirmation(utilisateur):
    return signing.dumps({"u": utilisateur.pk, "e": utilisateur.email}, salt=SEL_CONFIRMATION)


def lien_confirmation(utilisateur):
    return settings.SITE_URL.rstrip("/") + reverse("comptes:confirmer", args=[jeton_confirmation(utilisateur)])


def envoyer_confirmation(utilisateur):
    contexte = {"utilisateur": utilisateur, "lien": lien_confirmation(utilisateur)}
    send_mail(translation.gettext("Confirmez votre adresse e-mail — Le Grand Cinéma"),
              render_to_string("comptes/email_confirmation.txt", contexte), None, [utilisateur.email])


def confirmer(jeton):
    """Valide le lien reçu par e-mail. Renvoie l'utilisateur, ou None si le lien est faux ou trop ancien."""
    try:
        donnees = signing.loads(jeton, salt=SEL_CONFIRMATION, max_age=DUREE_LIEN_CONFIRMATION)
    except signing.BadSignature:
        return None
    utilisateur = get_user_model().objects.filter(pk=donnees.get("u"), email=donnees.get("e")).select_related("profil").first()
    if utilisateur is None or not hasattr(utilisateur, "profil"):
        return None
    if not utilisateur.profil.email_confirme:
        utilisateur.profil.email_confirme = True
        utilisateur.profil.save(update_fields=["email_confirme"])
        rattacher_reservations(utilisateur)
    return utilisateur


def rattacher_reservations(utilisateur):
    """Les réservations passées faites avec la même adresse rejoignent le compte (critère 2 de E9-US1)."""
    return (Reservation.objects.filter(compte__isnull=True, email__iexact=utilisateur.email)
            .update(compte=utilisateur))


def est_spectateur_confirme(utilisateur):
    profil = getattr(utilisateur, "profil", None)
    return bool(utilisateur.is_authenticated and profil and profil.email_confirme)


@transaction.atomic
def supprimer_compte(utilisateur):
    """RGPD : le compte et les données personnelles sont supprimés. Les réservations restent
    (comptabilité, statistiques) mais sans nom ni adresse e-mail."""
    Reservation.objects.filter(compte=utilisateur).update(nom="", email="", compte=None)
    utilisateur.delete()


def reservations_du_compte(utilisateur):
    return (Reservation.objects.filter(compte=utilisateur)
            .exclude(statut=Reservation.Statut.ATTENTE)
            .select_related("seance__film", "seance__salle").order_by("-seance__debut"))
