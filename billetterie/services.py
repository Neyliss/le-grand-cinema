"""
Billets : création, QR code, PDF, envoi par e-mail et contrôle à l'entrée.
"""
import base64
import io
import logging

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation

from reservation.models import PlaceSeance, Reservation

from .models import Billet

log = logging.getLogger(__name__)


# --- Création des billets -----------------------------------------------------------
@transaction.atomic
def creer_billets(reservation, tarifs_par_place):
    """Crée un billet par place avec le tarif choisi. Les billets restent sans valeur
    tant que la réservation n'est pas payée (voir Billet.est_valide)."""
    Billet.objects.filter(place__reservation=reservation).delete()
    billets = []
    for place in reservation.places.select_related("siege"):
        tarif = tarifs_par_place[place.id]
        billets.append(Billet.objects.create(place=place, tarif=tarif, prix=tarif.prix))
    return billets


# --- QR code et PDF ---------------------------------------------------------------
def qr_png(code, taille=8):
    import qrcode

    image = qrcode.make(code, box_size=taille, border=2)
    tampon = io.BytesIO()
    image.save(tampon, format="PNG")
    return tampon.getvalue()


def qr_data_uri(code):
    return "data:image/png;base64," + base64.b64encode(qr_png(code)).decode()


def pdf_billets(reservation):
    """Un billet par page (format A6), avec son QR code unique."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A6
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    largeur, hauteur = A6
    tampon = io.BytesIO()
    pdf = canvas.Canvas(tampon, pagesize=A6)
    pdf.setTitle(f"Billets {reservation.reference}")
    seance = reservation.seance
    debut = timezone.localtime(seance.debut)
    for billet in reservation.billets():
        pdf.setFillColor(colors.HexColor("#0E2250"))
        pdf.rect(0, hauteur - 34 * mm, largeur, 34 * mm, stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(8 * mm, hauteur - 9 * mm, "LE GRAND CINÉMA")
        pdf.setFont("Helvetica-Bold", 17)
        pdf.drawString(8 * mm, hauteur - 19 * mm, str(seance.film)[:28])
        pdf.setFont("Helvetica", 10)
        pdf.drawString(8 * mm, hauteur - 27 * mm, f"{debut:%d/%m/%Y} · {debut:%H:%M} · {seance.film.version}")
        pdf.setFillColor(colors.HexColor("#16242A"))
        infos = [("Salle", str(seance.salle)), ("Siège", str(billet.place.siege)), ("Tarif", billet.tarif.libelle),
                 ("Prix", f"{billet.prix} €".replace(".", ","))]
        y = hauteur - 44 * mm
        for i, (libelle, valeur) in enumerate(infos):
            x = 8 * mm + (i % 2) * 46 * mm
            yy = y - (i // 2) * 12 * mm
            pdf.setFont("Helvetica", 7.5)
            pdf.setFillColor(colors.HexColor("#5B6B72"))
            pdf.drawString(x, yy, libelle.upper())
            pdf.setFont("Helvetica-Bold", 11)
            pdf.setFillColor(colors.HexColor("#16242A"))
            pdf.drawString(x, yy - 5 * mm, valeur[:22])
        taille_qr = 46 * mm
        pdf.drawImage(ImageReader(io.BytesIO(qr_png(billet.code_qr))), (largeur - taille_qr) / 2, 16 * mm, taille_qr, taille_qr)
        pdf.setFont("Helvetica", 7.5)
        pdf.setFillColor(colors.HexColor("#5B6B72"))
        pdf.drawCentredString(largeur / 2, 11 * mm, f"Réservation {reservation.reference} · billet {billet.code_qr}")
        pdf.drawCentredString(largeur / 2, 7 * mm, "Valable une seule fois. À présenter à l'entrée de la salle.")
        pdf.showPage()
    pdf.save()
    return tampon.getvalue()


# --- Envoi par e-mail (composant C6 : Amazon SES) ---------------------------------------
def lien_billet(reservation):
    return settings.SITE_URL.rstrip("/") + reverse("billetterie:billet", args=[reservation.reference, reservation.jeton])


def finaliser_billets(reservation_id):
    """Étapes 12 et 13 du diagramme de séquence : enregistrer le PDF, puis envoyer le billet."""
    reservation = Reservation.objects.get(pk=reservation_id)
    pdf = pdf_billets(reservation)
    reservation.billets_pdf.save(f"{reservation.reference}.pdf", ContentFile(pdf), save=True)
    if reservation.email:
        try:
            envoyer_billets(reservation, pdf)
        except Exception:  # un e-mail en échec ne doit pas annuler la vente
            log.exception("Envoi du billet %s impossible", reservation.reference)


def envoyer_billets(reservation, pdf=None):
    contexte = {"reservation": reservation, "billets": reservation.billets(), "lien": lien_billet(reservation)}
    sujet = translation.gettext("Vos billets — %(film)s") % {"film": reservation.seance.film}
    message = EmailMultiAlternatives(sujet, render_to_string("billetterie/email_billets.txt", contexte),
                                     to=[reservation.email])
    message.attach_alternative(render_to_string("billetterie/email_billets.html", contexte), "text/html")
    message.attach(f"billets-{reservation.reference}.pdf", pdf or pdf_billets(reservation), "application/pdf")
    message.send()


def prevenir_annulation(reservation):
    if not reservation.email:
        return
    contexte = {"reservation": reservation}
    EmailMultiAlternatives(
        f"Séance annulée — {reservation.seance.film}",
        render_to_string("billetterie/email_annulation.txt", contexte),
        to=[reservation.email],
    ).send()


# --- Contrôle à l'entrée (E6-US2) -------------------------------------------------------------
@transaction.atomic
def controler_billet(code, seance=None):
    """Étapes 14 et 15 : vérifie le billet puis le marque « utilisé ». Un billet déjà scanné est refusé."""
    # Verrou sur la seule ligne du billet : deux agents qui scannent le même billet en même
    # temps ne peuvent pas le valider deux fois (PostgreSQL refuse de verrouiller les jointures).
    billet = (Billet.objects.select_for_update(of=("self",))
              .select_related("place__siege", "place__reservation__seance__film", "tarif")
              .filter(code_qr=code.strip()).first())
    if billet is None:
        return {"resultat": "refuse", "titre": "Billet inconnu", "detail": "Ce QR code ne correspond à aucun billet."}
    reservation = billet.place.reservation
    if reservation is None or not reservation.est_payee or billet.place.statut != PlaceSeance.Statut.VENDUE:
        return {"resultat": "refuse", "titre": "Billet non valable", "detail": "Réservation non payée ou annulée."}
    if reservation.seance.statut != reservation.seance.Statut.PUBLIEE:
        return {"resultat": "refuse", "titre": "Séance annulée", "detail": str(reservation.seance)}
    if seance is not None and reservation.seance_id != seance.id:
        return {"resultat": "refuse", "titre": "Mauvaise séance", "detail": f"Billet pour : {reservation.seance}"}
    detail = f"{reservation.seance.film} · {billet.place.siege} · {billet.tarif.libelle}"
    if billet.utilise_le:
        heure = timezone.localtime(billet.utilise_le)
        return {"resultat": "deja_utilise", "titre": "Billet déjà utilisé",
                "detail": f"Scanné à {heure:%H:%M} · entrée refusée"}
    billet.utilise_le = timezone.now()
    billet.save(update_fields=["utilise_le"])
    return {"resultat": "valide", "titre": "Billet valide", "detail": detail,
            "heure": f"{timezone.localtime(billet.utilise_le):%H:%M}"}
