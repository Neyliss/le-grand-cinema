"""
Paiement en ligne avec Stripe Checkout (dossier 3, figure 8, étapes 7 à 10).

Le spectateur saisit sa carte sur la page de Stripe : le cinéma ne voit jamais les données
bancaires. Stripe confirme ensuite le paiement par un message signé (webhook) que l'on vérifie.
Sans clé Stripe (développement), un « mode démonstration » simule le paiement.
"""
import logging
import time

from django.conf import settings
from django.db import transaction
from django.urls import reverse

from reservation.models import PlaceSeance, Reservation

from .models import Paiement

log = logging.getLogger(__name__)


class PaiementTropTardif(Exception):
    """Le paiement est arrivé après la libération des places : il est remboursé."""


def en_dict(objet):
    """Les objets renvoyés par Stripe deviennent de simples dictionnaires Python."""
    return objet if isinstance(objet, dict) else objet.to_dict()


def stripe_actif():
    return bool(settings.STRIPE_SECRET_KEY)


def client_stripe():
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def url_de_paiement(request, reservation):
    """Adresse vers laquelle envoyer le spectateur pour payer."""
    if not stripe_actif():
        return reverse("paiement:demo", args=[reservation.reference])
    stripe = client_stripe()
    lignes = [{
        "price_data": {
            "currency": "eur",
            "unit_amount": int(billet.prix * 100),
            "product_data": {"name": f"{reservation.seance.film} — {billet.tarif.libelle} — siège {billet.place.siege}"},
        },
        "quantity": 1,
    } for billet in reservation.billets()]
    retour = request.build_absolute_uri(reverse("paiement:retour", args=[reservation.reference]))
    annulation = request.build_absolute_uri(reverse("reservation:recapitulatif", args=[reservation.reference]))
    options = {"customer_email": reservation.email} if reservation.email else {}
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=lignes,
        client_reference_id=reservation.reference,
        metadata={"reservation": reservation.reference},
        success_url=retour + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=annulation,
        expires_at=int(time.time()) + 30 * 60,  # durée minimale imposée par Stripe
        locale="auto",
        **options,
    )
    return session.url


@transaction.atomic
def confirmer_paiement(reservation_id, mode, reference_stripe=""):
    """Étapes 10 et 11 : le paiement est confirmé, les sièges passent « vendus »,
    la réservation « payée ». Fonction idempotente : un second appel ne fait rien."""
    reservation = Reservation.objects.select_for_update().get(pk=reservation_id)
    if reservation.est_payee:
        return reservation
    places = list(reservation.places.select_for_update())
    billets = list(reservation.billets())
    if not places or len(billets) != len(places) or any(p.statut != PlaceSeance.Statut.BLOQUEE for p in places):
        # Le délai de 10 minutes est dépassé et les places ont été libérées : on rembourse.
        reservation.statut = Reservation.Statut.ANNULEE
        reservation.save(update_fields=["statut"])
        if reference_stripe:
            rembourser_reference(reference_stripe)
        raise PaiementTropTardif()
    for place in places:
        place.statut, place.fin_blocage = PlaceSeance.Statut.VENDUE, None
        place.save(update_fields=["statut", "fin_blocage"])
    reservation.statut = Reservation.Statut.PAYEE
    reservation.save(update_fields=["statut"])
    Paiement.objects.create(reservation=reservation, mode=mode, reference_stripe=reference_stripe,
                            montant=sum(b.prix for b in billets))
    # Étapes 12 et 13 : billet PDF enregistré puis envoyé, une fois la transaction validée.
    from billetterie.services import finaliser_billets

    transaction.on_commit(lambda: finaliser_billets(reservation.id))
    return reservation


def confirmer_session_stripe(session):
    """Traite une session Stripe Checkout payée (webhook ou retour du spectateur)."""
    session = en_dict(session)
    if session.get("payment_status") != "paid":
        return None
    reference = (session.get("metadata") or {}).get("reservation") or session.get("client_reference_id")
    reservation = Reservation.objects.filter(reference=reference).first()
    if reservation is None:
        log.warning("Session Stripe %s : réservation %s introuvable", session.get("id"), reference)
        return None
    return confirmer_paiement(reservation.id, Paiement.Mode.CARTE_EN_LIGNE, session.get("id", ""))


def rembourser_reference(reference_stripe):
    """Rembourse un paiement Stripe à partir de l'identifiant de la session Checkout."""
    if not stripe_actif() or not reference_stripe.startswith("cs_"):
        return
    stripe = client_stripe()
    session = en_dict(stripe.checkout.Session.retrieve(reference_stripe))
    if session.get("payment_intent"):
        stripe.Refund.create(payment_intent=session["payment_intent"])


def rembourser(reservation):
    """Rembourse une réservation payée (utilisé lors de l'annulation d'une séance)."""
    paiement = getattr(reservation, "paiement", None)
    if paiement is None or paiement.statut == Paiement.Statut.REMBOURSE:
        return
    if paiement.mode == Paiement.Mode.CARTE_EN_LIGNE:
        rembourser_reference(paiement.reference_stripe)
    # Au guichet, le remboursement se fait sur place : on le note simplement.
    paiement.statut = Paiement.Statut.REMBOURSE
    paiement.save(update_fields=["statut"])
