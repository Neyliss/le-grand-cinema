"""Bug trouvé en relisant le parcours de réservation (bloc 3, dossier 3, question 3).

Situation : un spectateur est sur la page de paiement de Stripe ; pendant ce temps, la direction
annule la séance. L'annulation ne traitait que les réservations déjà payées : le paiement était
ensuite accepté, des billets étaient envoyés pour une séance annulée, et rien n'était remboursé.
"""
from unittest import mock

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from outils_de_test.fabriques import creer_seance, reserver_avec_billets
from paiement.models import Paiement
from paiement.services import PaiementTropTardif, confirmer_paiement
from reservation.models import PlaceSeance, Reservation
from reservation.services import annuler_seance


class PaiementSeanceAnnuleeTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        self.reservation = reserver_avec_billets(self.seance, nb=2)  # le spectateur est en train de payer

    def test_le_paiement_arrive_apres_l_annulation_il_est_rembourse_et_aucun_billet_n_est_envoye(self):
        annuler_seance(self.seance)

        with mock.patch("paiement.services.rembourser_reference") as rembourser, \
                self.captureOnCommitCallbacks(execute=True), self.assertRaises(PaiementTropTardif):
            confirmer_paiement(self.reservation.id, Paiement.Mode.CARTE_EN_LIGNE, "cs_test_annulee")

        rembourser.assert_called_once_with("cs_test_annulee")
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.Statut.ANNULEE)
        self.assertFalse(PlaceSeance.objects.filter(statut=PlaceSeance.Statut.VENDUE).exists())
        self.assertEqual(mail.outbox, [])  # aucun billet envoyé

    def test_l_annulation_libere_aussi_les_places_en_cours_de_paiement(self):
        annuler_seance(self.seance)

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.Statut.ANNULEE)
        self.assertFalse(self.seance.places.filter(statut=PlaceSeance.Statut.BLOQUEE).exists())

    def test_le_spectateur_ne_peut_plus_aller_payer_une_seance_annulee(self):
        sieges = [s.id for s in self.seance.salle.sieges.all()[10:12]]
        self.client.post(reverse("reservation:bloquer", args=[self.seance.id]), {"sieges": sieges})
        en_cours = Reservation.objects.get(statut=Reservation.Statut.ATTENTE, places__siege_id=sieges[0])

        annuler_seance(self.seance)
        page = self.client.get(reverse("reservation:recapitulatif", args=[en_cours.reference]))

        self.assertContains(page, "annulée")
        self.assertNotContains(page, 'id="bouton-payer"')
