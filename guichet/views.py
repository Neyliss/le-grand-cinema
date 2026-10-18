"""
Vente au guichet (EPIC E6) : même outil et même stock de places que le site.
Une place vendue ici disparaît aussitôt du plan en ligne, et inversement.
"""
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from billetterie.services import creer_billets, qr_data_uri
from catalogue.models import Seance, Tarif
from grandcinema.acces import agent_requis
from paiement.models import Paiement
from paiement.services import confirmer_paiement
from reservation.models import Reservation
from reservation.services import SeanceNonReservable, SiegeIndisponible, compter_places, creer_reservation, plan_de_salle

MODES = {"carte": Paiement.Mode.GUICHET_CARTE, "especes": Paiement.Mode.GUICHET_ESPECES}


@agent_requis
def tableau(request):
    seances = list(Seance.objects.filter(debut__date=timezone.localdate(), statut=Seance.Statut.PUBLIEE)
                   .select_related("film", "salle"))
    for s in seances:
        c = compter_places(s)
        s.total_places = sum(c.values())
        s.taux = round(100 * c["vendues"] / s.total_places) if s.total_places else 0
        s.nb_libres = c["libres"]
    choisie = None
    if request.GET.get("seance", "").isdigit():
        choisie = next((s for s in seances if s.id == int(request.GET["seance"])), None)
    if choisie is None:
        choisie = next((s for s in seances if s.est_reservable), None)
    return render(request, "guichet/tableau.html", {
        "seances": seances,
        "seance": choisie,
        "plan": plan_de_salle(choisie) if choisie else None,
        "tarifs": Tarif.objects.filter(actif=True),
        "maintenant": timezone.localtime(),
    })


@agent_requis
@require_POST
def vendre(request, seance_id):
    seance = get_object_or_404(Seance, pk=seance_id)
    ids = [int(i) for i in request.POST.getlist("sieges") if i.isdigit()]
    mode = MODES.get(request.POST.get("mode"), Paiement.Mode.GUICHET_CARTE)
    tarifs = {t.id: t for t in Tarif.objects.filter(actif=True)}
    retour = reverse("guichet:tableau") + f"?seance={seance.id}"
    try:
        with transaction.atomic():
            reservation = creer_reservation(seance, ids, canal=Reservation.Canal.GUICHET)
            choix = {}
            for place in reservation.places.all():
                tarif_id = request.POST.get(f"tarif_{place.siege_id}", "")
                choix[place.id] = tarifs.get(int(tarif_id)) if tarif_id.isdigit() else None
                if choix[place.id] is None:
                    raise ValueError("tarif manquant")
            creer_billets(reservation, choix)
            confirmer_paiement(reservation.id, mode)
    except SiegeIndisponible:
        messages.error(request, "Un siège vient d'être pris en ligne : la vente est annulée, choisissez d'autres places.")
        return redirect(retour)
    except (SeanceNonReservable, ValueError):
        messages.error(request, "Vente impossible : vérifiez la séance et les tarifs.")
        return redirect(retour)
    messages.success(request, f"Vente {reservation.reference} enregistrée.")
    return redirect("guichet:imprimer", reference=reservation.reference)


@agent_requis
def imprimer(request, reference):
    reservation = get_object_or_404(Reservation.objects.select_related("seance__film", "seance__salle"), reference=reference)
    billets = [(b, qr_data_uri(b.code_qr)) for b in reservation.billets()]
    return render(request, "guichet/imprimer.html", {"reservation": reservation, "billets": billets})
