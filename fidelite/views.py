"""Achat en ligne d'une carte d'abonnement (E10-US1)."""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from comptes.services import est_spectateur_confirme
from paiement.services import client_stripe, en_dict, stripe_actif

from .models import Abonnement, FormuleAbonnement
from .services import CarteDejaActive, activer, carte_active, commander, url_de_paiement_carte


def carte_du_spectateur(request, reference):
    """Une carte n'est visible que par son propriétaire."""
    return get_object_or_404(Abonnement.objects.select_related("formule"), reference=reference, compte=request.user)


@login_required
def abonnement(request):
    if not est_spectateur_confirme(request.user):
        raise Http404
    if request.method == "POST":
        formule = get_object_or_404(FormuleAbonnement, pk=request.POST.get("formule", 0) or 0, actif=True)
        try:
            carte = commander(request.user, formule)
        except CarteDejaActive:
            messages.info(request, _("Votre carte a encore des places : vous pourrez en acheter une nouvelle quand elle sera épuisée."))
            return redirect("comptes:mon_compte")
        return redirect(url_de_paiement_carte(request, carte))
    return render(request, "fidelite/abonnement.html", {
        "formules": FormuleAbonnement.objects.filter(actif=True),
        "carte": carte_active(request.user),
        "stripe": stripe_actif(),
    })


@login_required
def demo(request, reference):
    """Mode démonstration (aucune clé Stripe) : le paiement de la carte est simulé."""
    if not settings.PAIEMENT_DEMO:
        raise Http404
    carte = carte_du_spectateur(request, reference)
    if request.method == "POST":
        activer(carte.id, f"demo-{carte.reference}")
        messages.success(request, _("Votre carte d'abonnement est active."))
        return redirect("comptes:mon_compte")
    return render(request, "fidelite/demo.html", {"carte": carte})


@login_required
def retour(request, reference):
    """Retour depuis Stripe : la session est vérifiée auprès de Stripe avant d'activer la carte."""
    carte = carte_du_spectateur(request, reference)
    session_id = request.GET.get("session_id", "")
    if stripe_actif() and session_id.startswith("cs_") and carte.statut == Abonnement.Statut.ATTENTE:
        session = en_dict(client_stripe().checkout.Session.retrieve(session_id))
        if session.get("payment_status") == "paid" and (session.get("metadata") or {}).get("abonnement") == carte.reference:
            activer(carte.id, session_id)
    carte.refresh_from_db()
    if carte.statut == Abonnement.Statut.ACTIVE:
        messages.success(request, _("Votre carte d'abonnement est active."))
    else:
        messages.info(request, _("Paiement en cours de vérification : votre carte sera active dans quelques instants."))
    return redirect("comptes:mon_compte")
