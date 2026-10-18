"""Vente au guichet (E6-US1) : une place vendue au guichet n'est plus proposée en ligne."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from catalogue.models import Tarif
from reservation.models import PlaceSeance, Reservation
from reservation.services import creer_reservation, plan_de_salle
from reservation.tests import creer_seance


class GuichetTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        self.client.force_login(User.objects.create_user("agent", password="x", is_staff=True))
        self.tarif = Tarif.objects.first()

    def test_vente_au_guichet_retire_la_place_du_site(self):
        siege = self.seance.salle.sieges.first()
        reponse = self.client.post(reverse("guichet:vendre", args=[self.seance.id]),
                                   {"sieges": [siege.id], f"tarif_{siege.id}": self.tarif.id, "mode": "especes"})
        reservation = Reservation.objects.get()
        self.assertRedirects(reponse, reverse("guichet:imprimer", args=[reservation.reference]))
        self.assertEqual(reservation.canal, Reservation.Canal.GUICHET)
        self.assertEqual(reservation.paiement.mode, "guichet_especes")
        statuts = {s["id"]: s["statut"] for r in plan_de_salle(self.seance)["rangees"] for s in r["sieges"]}
        self.assertEqual(statuts[siege.id], PlaceSeance.Statut.VENDUE)

    def test_vente_refusee_si_le_siege_est_bloque_en_ligne(self):
        siege = self.seance.salle.sieges.first()
        creer_reservation(self.seance, [siege.id])  # un spectateur est en train de payer en ligne
        self.client.post(reverse("guichet:vendre", args=[self.seance.id]),
                         {"sieges": [siege.id], f"tarif_{siege.id}": self.tarif.id, "mode": "carte"})
        self.assertEqual(Reservation.objects.filter(canal=Reservation.Canal.GUICHET).count(), 0)

    def test_guichet_interdit_au_public(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("guichet:tableau")).status_code, 302)
