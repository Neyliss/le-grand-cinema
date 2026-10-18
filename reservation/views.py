"""
Parcours de réservation en ligne (EPICs E2 et E3), étapes 1 à 8 du diagramme de séquence.
"""
from django import forms
from django.conf import settings
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from billetterie.services import creer_billets
from catalogue.models import Seance, Tarif
from grandcinema.acces import est_agent
from paiement.services import stripe_actif, url_de_paiement

from .models import Reservation
from .services import SeanceNonReservable, SiegeIndisponible, creer_reservation, places_encore_bloquees, plan_de_salle

CLE_SESSION = "reservations"


def seance_reservable_ou_404(seance_id):
    return get_object_or_404(Seance.objects.select_related("film", "salle"), pk=seance_id, statut=Seance.Statut.PUBLIEE)


def plan(request, seance_id):
    """Étapes 1 à 3 : le spectateur choisit une séance et voit le plan de salle à jour."""
    seance = seance_reservable_ou_404(seance_id)
    if not seance.est_reservable:
        messages.info(request, _("Cette séance a déjà commencé : choisissez une autre séance."))
        return redirect("catalogue:programmation")
    return render(request, "reservation/plan.html", {
        "seance": seance,
        "plan": plan_de_salle(seance),
        "max_places": settings.PLACES_MAX_PAR_RESERVATION,
        "rafraichissement": settings.RAFRAICHISSEMENT_PLAN_SECONDES,
        "duree_blocage": settings.DUREE_BLOCAGE_MINUTES,
    })


@never_cache
def api_plan(request, seance_id):
    """Plan de salle en JSON, lu par JavaScript toutes les 5 secondes (E2-US1)."""
    seance = seance_reservable_ou_404(seance_id)
    return JsonResponse(plan_de_salle(seance))


@require_POST
def bloquer(request, seance_id):
    """Étapes 4 à 6 : les sièges choisis sont verrouillés puis bloqués 10 minutes."""
    seance = seance_reservable_ou_404(seance_id)
    ids = [int(i) for i in request.POST.getlist("sieges") if i.isdigit()]
    try:
        reservation = creer_reservation(seance, ids)
    except SiegeIndisponible:
        messages.error(request, _("Un des sièges choisis vient d'être pris. Choisissez d'autres places."))
        return redirect("reservation:plan", seance_id=seance.id)
    except SeanceNonReservable:
        messages.error(request, _("Cette séance n'est plus en vente."))
        return redirect("catalogue:programmation")
    request.session[CLE_SESSION] = request.session.get(CLE_SESSION, [])[-9:] + [reservation.reference]
    return redirect("reservation:recapitulatif", reference=reservation.reference)


class RecapitulatifForm(forms.Form):
    """Tarif de chaque place, puis nom et e-mail : la réservation ne demande rien d'autre (E3-US1)."""

    nom = forms.CharField(label=gettext_lazy("Nom"), max_length=100)
    email = forms.EmailField(label=gettext_lazy("Adresse e-mail"))

    def __init__(self, *args, places, **kwargs):
        super().__init__(*args, **kwargs)
        self.places = places
        tarifs = Tarif.objects.filter(actif=True)
        for place in places:
            champ = self.fields[f"tarif_{place.id}"] = forms.ModelChoiceField(
                queryset=tarifs, empty_label=None, label=str(place.siege),
                widget=forms.Select(attrs={"data-siege": str(place.siege)}),
                initial=getattr(getattr(place, "billet", None), "tarif_id", None) or tarifs.first())
            champ.label_from_instance = lambda tarif: tarif.libelle  # le prix est affiché à côté

    def tarifs_par_place(self):
        return {place.id: self.cleaned_data[f"tarif_{place.id}"] for place in self.places}

    def champs_tarifs(self):
        return [(place, self[f"tarif_{place.id}"]) for place in self.places]


def reservation_du_visiteur(request, reference):
    """Une réservation n'est visible que par le navigateur qui l'a créée (ou par le personnel)."""
    reservation = get_object_or_404(Reservation.objects.select_related("seance__film", "seance__salle"), reference=reference)
    if reference not in request.session.get(CLE_SESSION, []) and not est_agent(request.user):
        raise Http404
    return reservation


def recapitulatif(request, reference):
    """Choix des tarifs, nom et e-mail, puis départ vers la page de paiement (étapes 7 et 8)."""
    reservation = reservation_du_visiteur(request, reference)
    if reservation.est_payee:
        return redirect("billetterie:billet", reservation.reference, reservation.jeton)
    if reservation.statut == Reservation.Statut.ANNULEE or not places_encore_bloquees(reservation):
        return render(request, "reservation/expiree.html", {"reservation": reservation})

    places = list(reservation.places.select_related("siege", "billet"))
    form = RecapitulatifForm(request.POST or None, places=places,
                             initial={"nom": reservation.nom, "email": reservation.email})
    if request.method == "POST" and form.is_valid():
        reservation.nom = form.cleaned_data["nom"]
        reservation.email = form.cleaned_data["email"]
        reservation.save(update_fields=["nom", "email"])
        creer_billets(reservation, form.tarifs_par_place())
        return redirect(url_de_paiement(request, reservation))

    return render(request, "reservation/recapitulatif.html", {
        "reservation": reservation,
        "seance": reservation.seance,
        "form": form,
        "fin_blocage": reservation.fin_blocage(),
        "prix_tarifs": {str(t.id): str(t.prix) for t in Tarif.objects.filter(actif=True)},
        "stripe": stripe_actif(),
    })
