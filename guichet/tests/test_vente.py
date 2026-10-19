"""E6-US1 : une place vendue au guichet n'est plus proposée en ligne, et inversement."""
from django.test import TestCase
from django.urls import reverse

from catalogue.models import Tarif
from outils_de_test.fabriques import creer_agent, creer_seance
from reservation.models import PlaceSeance, Reservation
from reservation.services import creer_reservation, plan_de_salle


class VenteAuGuichetTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        self.siege = self.seance.salle.sieges.first()
        self.tarif = Tarif.objects.first()
        self.client.force_login(creer_agent())

    def vendre_au_guichet(self, mode):
        return self.client.post(reverse("guichet:vendre", args=[self.seance.id]),
                                {"sieges": [self.siege.id], f"tarif_{self.siege.id}": self.tarif.id, "mode": mode})

    def test_vente_au_guichet_retire_la_place_du_site(self):
        reponse = self.vendre_au_guichet("especes")

        reservation = Reservation.objects.get()
        self.assertRedirects(reponse, reverse("guichet:imprimer", args=[reservation.reference]))
        self.assertEqual(reservation.canal, Reservation.Canal.GUICHET)
        self.assertEqual(reservation.paiement.mode, "guichet_especes")
        statuts = {s["id"]: s["statut"] for r in plan_de_salle(self.seance)["rangees"] for s in r["sieges"]}
        self.assertEqual(statuts[self.siege.id], PlaceSeance.Statut.VENDUE)

    def test_vente_refusee_si_le_siege_est_bloque_en_ligne(self):
        creer_reservation(self.seance, [self.siege.id])  # un spectateur est en train de payer en ligne

        self.vendre_au_guichet("carte")

        self.assertEqual(Reservation.objects.filter(canal=Reservation.Canal.GUICHET).count(), 0)
