"""Test d'intégration : parcours complet du spectateur, du choix des sièges à l'e-mail avec le billet."""
import tempfile
from decimal import Decimal

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from catalogue.models import Tarif
from outils_de_test.fabriques import creer_seance
from reservation.models import PlaceSeance, Reservation
from reservation.services import creer_reservation


@override_settings(PAIEMENT_DEMO=True, STRIPE_SECRET_KEY="", MEDIA_ROOT=tempfile.mkdtemp())
class ParcoursEnLigneTests(TestCase):
    """Parcours en mode démonstration (sans clé Stripe) : aucun appel à Internet."""

    def test_reservation_paiement_et_billet(self):
        seance = creer_seance()
        sieges = list(seance.salle.sieges.all()[:2])

        # 1. Choix des sièges : ils sont bloqués et le spectateur passe au récapitulatif
        reponse = self.client.post(reverse("reservation:bloquer", args=[seance.id]), {"sieges": [s.id for s in sieges]})
        reservation = Reservation.objects.get()
        self.assertRedirects(reponse, reverse("reservation:recapitulatif", args=[reservation.reference]))

        # 2. Tarifs et coordonnées : direction la page de paiement
        donnees = {"nom": "Marie Dupont", "email": "marie@exemple.fr"}
        for place in reservation.places.all():
            donnees[f"tarif_{place.id}"] = Tarif.objects.get().id
        reponse = self.client.post(reverse("reservation:recapitulatif", args=[reservation.reference]), donnees)
        self.assertRedirects(reponse, reverse("paiement:demo", args=[reservation.reference]))

        # 3. Paiement : places vendues, réservation payée, billet affiché
        with self.captureOnCommitCallbacks(execute=True):
            reponse = self.client.post(reverse("paiement:demo", args=[reservation.reference]))
        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, Reservation.Statut.PAYEE)
        self.assertRedirects(reponse, reverse("billetterie:billet", args=[reservation.reference, reservation.jeton]))
        self.assertTrue(all(p.statut == PlaceSeance.Statut.VENDUE for p in reservation.places.all()))
        self.assertEqual(reservation.paiement.montant, Decimal("20.00"))

        # 4. E-mail : un message au spectateur, avec le billet PDF en pièce jointe
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["marie@exemple.fr"])
        self.assertEqual(mail.outbox[0].attachments[0][2], "application/pdf")

    def test_la_reservation_d_un_autre_navigateur_est_invisible(self):
        seance = creer_seance()
        reservation = creer_reservation(seance, [seance.salle.sieges.first().id])

        # La page refuse l'accès (404) ; Django écrit ce refus dans son journal, que l'on capture
        with self.assertLogs("django.request", "WARNING"):
            reponse = self.client.get(reverse("reservation:recapitulatif", args=[reservation.reference]))

        self.assertEqual(reponse.status_code, 404)
