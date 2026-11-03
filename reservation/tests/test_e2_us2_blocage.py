"""E2-US2 : en tant que spectateur, je veux que mes sièges soient bloqués pendant le paiement,
afin de ne pas les perdre. Un test par critère d'acceptation de la carte Trello."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from outils_de_test.fabriques import creer_agent, creer_seance
from reservation.models import PlaceSeance, Reservation
from reservation.services import SiegeIndisponible, creer_reservation, liberer_places_expirees


class BlocageTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        self.siege = self.seance.salle.sieges.first()

    def reserver(self):
        reponse = self.client.post(reverse("reservation:bloquer", args=[self.seance.id]), {"sieges": [self.siege.id]})
        return Reservation.objects.get(), reponse

    def test_critere_1_bloques_10_minutes_puis_liberes_si_le_paiement_n_aboutit_pas(self):
        reservation, _ = self.reserver()
        place = reservation.places.get()
        self.assertEqual(place.statut, PlaceSeance.Statut.BLOQUEE)
        self.assertAlmostEqual((place.fin_blocage - timezone.now()).total_seconds(), 600, delta=5)

        reservation.places.update(fin_blocage=timezone.now() - timedelta(seconds=1))
        liberer_places_expirees()
        self.assertEqual(self.seance.places.get(siege=self.siege).statut, PlaceSeance.Statut.LIBRE)

    def test_critere_2_un_minuteur_affiche_le_temps_restant(self):
        reservation, reponse = self.reserver()

        page = self.client.get(reponse.url)
        self.assertContains(page, 'id="minuteur"')
        self.assertContains(page, f'data-fin="{timezone.localtime(reservation.fin_blocage()).isoformat()[:19]}')

    def test_critere_3_personne_d_autre_ne_peut_prendre_ces_sieges_ni_en_ligne_ni_au_guichet(self):
        self.reserver()

        with self.assertRaises(SiegeIndisponible):
            creer_reservation(self.seance, [self.siege.id])  # autre spectateur
        self.client.force_login(creer_agent())
        self.client.post(reverse("guichet:vendre", args=[self.seance.id]), {"sieges": [self.siege.id]})
        self.assertFalse(PlaceSeance.objects.filter(statut=PlaceSeance.Statut.VENDUE).exists())

    def test_changer_de_places_rend_les_sieges_tout_de_suite(self):
        reservation, reponse = self.reserver()

        retour = self.client.post(reverse("reservation:liberer", args=[reservation.reference]))

        self.assertRedirects(retour, reverse("reservation:plan", args=[self.seance.id]))
        self.assertEqual(self.seance.places.get(siege=self.siege).statut, PlaceSeance.Statut.LIBRE)
        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, Reservation.Statut.ANNULEE)
