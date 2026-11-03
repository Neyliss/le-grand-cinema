"""Billet du spectateur (E4) et contrôle à l'entrée par les agents d'accueil (E6)."""
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import translation
from django.utils.translation import gettext as _
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from catalogue.models import Seance
from grandcinema.acces import agent_requis
from reservation.models import PlaceSeance, Reservation

from .models import Billet
from .services import annuler_entree, controler_billet, envoyer_billets, pdf_billets, qr_data_uri


def reservation_payee(reference, jeton):
    reservation = get_object_or_404(Reservation.objects.select_related("seance__film", "seance__salle"),
                                    reference=reference, jeton=jeton)
    if not reservation.est_payee:
        raise Http404
    return reservation


@require_GET
def billet(request, reference, jeton):
    """Confirmation de réservation et billets avec QR code (lien envoyé par e-mail)."""
    reservation = reservation_payee(reference, jeton)
    billets = [(b, qr_data_uri(b.code_qr)) for b in reservation.billets()]
    return render(request, "billetterie/billet.html", {"reservation": reservation, "billets": billets})


RENVOIS_MAX = 3  # par réservation et par navigateur : évite d'envoyer des e-mails en rafale


@require_POST
def renvoyer(request, reference, jeton):
    """« Renvoyer mon billet » : si l'e-mail n'est pas arrivé, le spectateur le redemande lui-même."""
    reservation = reservation_payee(reference, jeton)
    cle = f"renvois-{reservation.reference}"
    if not reservation.email or request.session.get(cle, 0) >= RENVOIS_MAX:
        messages.error(request, _("Le billet ne peut plus être renvoyé : téléchargez-le en PDF ci-dessous."))
    else:
        with translation.override(reservation.langue):
            envoyer_billets(reservation)
        request.session[cle] = request.session.get(cle, 0) + 1
        messages.success(request, _("Le billet a été renvoyé à %(email)s.") % {"email": reservation.email})
    return redirect("billetterie:billet", reservation.reference, reservation.jeton)


@require_GET
def billet_pdf(request, reference, jeton):
    reservation = reservation_payee(reference, jeton)
    if reservation.billets_pdf:
        fichier = reservation.billets_pdf.open("rb")
    else:  # PDF pas encore enregistré : on le génère à la volée
        import io

        fichier = io.BytesIO(pdf_billets(reservation))
    return FileResponse(fichier, as_attachment=True, filename=f"billets-{reservation.reference}.pdf",
                        content_type="application/pdf")


# --- Contrôle à l'entrée (agents d'accueil) ----------------------------------------------
@agent_requis
def controle_seances(request):
    seances = Seance.objects.filter(debut__date=timezone.localdate()).select_related("film", "salle")
    return render(request, "billetterie/controle_seances.html", {"seances": seances})


def compteur_entrees(seance):
    vendus = Billet.objects.filter(place__seance=seance, place__statut=PlaceSeance.Statut.VENDUE)
    return {"entrees": vendus.filter(utilise_le__isnull=False).count(), "vendus": vendus.count()}


@agent_requis
def controle(request, seance_id):
    seance = get_object_or_404(Seance.objects.select_related("film", "salle"), pk=seance_id)
    return render(request, "billetterie/controle.html", {"seance": seance, "compteur": compteur_entrees(seance)})


@agent_requis
@require_POST
def controle_verifier(request, seance_id):
    seance = get_object_or_404(Seance, pk=seance_id)
    resultat = controler_billet(request.POST.get("code", ""), seance)
    resultat["compteur"] = compteur_entrees(seance)
    return JsonResponse(resultat)


@agent_requis
@require_POST
def controle_annuler(request, seance_id):
    seance = get_object_or_404(Seance, pk=seance_id)
    resultat = annuler_entree(request.POST.get("code", ""), seance)
    resultat["compteur"] = compteur_entrees(seance)
    return JsonResponse(resultat)
