"""
Paiement : retour depuis Stripe, webhook signé, et page de démonstration sans clé Stripe.
"""
import logging

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from reservation.views import reservation_du_visiteur

from .models import Paiement
from .services import PaiementTropTardif, client_stripe, confirmer_paiement, confirmer_session_stripe, en_dict, stripe_actif

log = logging.getLogger(__name__)


def demo(request, reference):
    """Mode démonstration (aucune clé Stripe) : simule la page de paiement de Stripe."""
    if not settings.PAIEMENT_DEMO:
        raise Http404
    reservation = reservation_du_visiteur(request, reference)
    if reservation.est_payee:
        return redirect("billetterie:billet", reservation.reference, reservation.jeton)
    if request.method == "POST":
        try:
            confirmer_paiement(reservation.id, Paiement.Mode.CARTE_EN_LIGNE, f"demo-{reservation.reference}")
        except PaiementTropTardif:
            return render(request, "reservation/expiree.html", {"reservation": reservation, "rembourse": True})
        return redirect("billetterie:billet", reservation.reference, reservation.jeton)
    return render(request, "paiement/demo.html", {"reservation": reservation, "billets": reservation.billets()})


def retour(request, reference):
    """Le spectateur revient de Stripe. On vérifie la session auprès de Stripe (sans attendre le webhook)."""
    reservation = reservation_du_visiteur(request, reference)
    session_id = request.GET.get("session_id", "")
    if stripe_actif() and session_id.startswith("cs_") and not reservation.est_payee:
        session = en_dict(client_stripe().checkout.Session.retrieve(session_id))
        if (session.get("metadata") or {}).get("reservation") == reservation.reference:
            try:
                confirmer_session_stripe(session)
            except PaiementTropTardif:
                return render(request, "reservation/expiree.html", {"reservation": reservation, "rembourse": True})
            reservation.refresh_from_db()
    if reservation.est_payee:
        return redirect("billetterie:billet", reservation.reference, reservation.jeton)
    return render(request, "paiement/attente.html", {"reservation": reservation})


@csrf_exempt
@require_POST
def webhook_stripe(request):
    """Étape 10 : confirmation signée envoyée par Stripe. La signature est vérifiée avant tout traitement."""
    if not stripe_actif():
        raise Http404
    stripe = client_stripe()
    try:
        evenement = stripe.Webhook.construct_event(
            request.body, request.headers.get("Stripe-Signature", ""), settings.STRIPE_WEBHOOK_SECRET)
    except Exception:  # signature absente ou fausse : message refusé
        log.warning("Webhook Stripe refusé : signature invalide")
        return HttpResponse(status=400)
    evenement = en_dict(evenement)
    if evenement["type"] in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        try:
            confirmer_session_stripe(evenement["data"]["object"])
        except PaiementTropTardif:
            log.warning("Paiement arrivé après la libération des places : remboursé")
    return HttpResponse(status=200)
