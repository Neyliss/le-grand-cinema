"""Règles de la fidélité (E10-US1) : achat d'une carte, décompte à chaque réservation, offres."""
import time

from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage, get_connection
from django.db import transaction
from django.db.models import F
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from paiement.services import PaiementTropTardif, client_stripe, stripe_actif

from .models import Abonnement


class CarteEpuisee(PaiementTropTardif):
    """La carte n'a plus assez de places au moment de confirmer : rien n'est décompté, l'éventuel paiement est remboursé."""


class CarteDejaActive(Exception):
    """Une nouvelle carte ne s'achète que lorsque la précédente est épuisée."""


def carte_active(compte):
    """La carte du spectateur qui a encore des places, ou None."""
    if compte is None or not getattr(compte, "is_authenticated", False):
        return None
    return (Abonnement.objects.filter(compte=compte, statut=Abonnement.Statut.ACTIVE, places_restantes__gt=0)
            .select_related("formule").first())


def commander(compte, formule):
    """Crée la carte « en attente de paiement »."""
    if carte_active(compte) is not None:
        raise CarteDejaActive()
    return Abonnement.objects.create(compte=compte, formule=formule, prix=formule.prix)


@transaction.atomic
def activer(abonnement_id, reference_stripe=""):
    """Paiement reçu : la carte reçoit ses places. Fonction idempotente (webhook et retour peuvent arriver tous les deux)."""
    carte = Abonnement.objects.select_for_update().select_related("formule").get(pk=abonnement_id)
    if carte.statut == Abonnement.Statut.ACTIVE:
        return carte
    carte.statut = Abonnement.Statut.ACTIVE
    carte.places_restantes = carte.formule.nb_places
    carte.reference_stripe = reference_stripe
    carte.active_le = timezone.now()
    carte.save()
    return carte


def url_de_paiement_carte(request, carte):
    """Même chemin de paiement que pour un billet : Stripe Checkout, ou la page de démonstration."""
    if not stripe_actif():
        return reverse("fidelite:demo", args=[carte.reference])
    retour = request.build_absolute_uri(reverse("fidelite:retour", args=[carte.reference]))
    session = client_stripe().checkout.Session.create(
        mode="payment",
        line_items=[{"price_data": {"currency": "eur", "unit_amount": int(carte.prix * 100),
                                    "product_data": {"name": f"Le Grand Cinéma — {carte.formule.libelle}"}},
                     "quantity": 1}],
        client_reference_id=carte.reference,
        metadata={"abonnement": carte.reference},
        customer_email=carte.compte.email,
        success_url=retour + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri(reverse("fidelite:abonnement")),
        expires_at=int(time.time()) + 30 * 60,
    )
    return session.url


def nb_places_abonne(billets):
    return sum(1 for billet in billets if billet.tarif.reserve_abonnes)


def decompter(reservation, billets):
    """Appelé pendant la confirmation du paiement (même transaction) : les places au tarif « abonné »
    sont retirées de la carte. Si la carte n'en a plus assez, rien n'est vendu."""
    nb = nb_places_abonne(billets)
    if not nb:
        return
    carte = None
    if reservation.compte_id:
        carte = (Abonnement.objects.select_for_update()
                 .filter(compte_id=reservation.compte_id, statut=Abonnement.Statut.ACTIVE, places_restantes__gte=nb)
                 .first())
    if carte is None:
        raise CarteEpuisee()
    Abonnement.objects.filter(pk=carte.pk).update(places_restantes=F("places_restantes") - nb)
    reservation.abonnement = carte
    reservation.save(update_fields=["abonnement"])


def recrediter(reservation):
    """Séance annulée : les places prises avec la carte lui sont rendues."""
    if reservation.abonnement_id:
        nb = nb_places_abonne(reservation.billets())
        Abonnement.objects.filter(pk=reservation.abonnement_id).update(places_restantes=F("places_restantes") + nb)


def destinataires_offres():
    """Seulement les spectateurs qui ont accepté les offres et confirmé leur adresse (RGPD)."""
    return list(get_user_model().objects.filter(profil__accepte_offres=True, profil__email_confirme=True, is_active=True)
                .values_list("email", flat=True))


def envoyer_offre(offre, site_url):
    """Un e-mail par destinataire : personne ne voit l'adresse des autres."""
    corps = render_to_string("fidelite/email_offre.txt", {"offre": offre, "lien_compte": site_url.rstrip("/") + reverse("comptes:mon_compte")})
    messages = [EmailMessage(offre.titre, corps, None, [email]) for email in destinataires_offres()]
    get_connection().send_messages(messages)
    offre.envoyee_le, offre.nb_destinataires = timezone.now(), len(messages)
    offre.save(update_fields=["envoyee_le", "nb_destinataires"])
    return len(messages)
