"""RG-02 : les sièges choisis sont bloqués 10 minutes, puis libérés s'ils ne sont pas payés."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from outils_de_test.fabriques import creer_seance
from reservation.models import PlaceSeance, Reservation
from reservation.services import creer_reservation, liberer_places_expirees


class BlocageDixMinutesTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        self.siege = self.seance.salle.sieges.first()

    def test_les_sieges_sont_bloques_dix_minutes(self):
        reservation = creer_reservation(self.seance, [self.siege.id])

        place = reservation.places.get()

        self.assertEqual(place.statut, PlaceSeance.Statut.BLOQUEE)
        restant = place.fin_blocage - timezone.now()
        self.assertTrue(timedelta(minutes=9) < restant <= timedelta(minutes=10))

    def test_un_blocage_expire_libere_le_siege(self):
        reservation = creer_reservation(self.seance, [self.siege.id])
        reservation.places.update(fin_blocage=timezone.now() - timedelta(seconds=1))

        nb_liberees = liberer_places_expirees()

        self.assertEqual(nb_liberees, 1)
        self.assertEqual(self.seance.places.get(siege=self.siege).statut, PlaceSeance.Statut.LIBRE)
        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, Reservation.Statut.ANNULEE)

    def test_un_autre_spectateur_peut_reprendre_un_siege_expire(self):
        premiere = creer_reservation(self.seance, [self.siege.id])
        premiere.places.update(fin_blocage=timezone.now() - timedelta(seconds=1))

        seconde = creer_reservation(self.seance, [self.siege.id])

        self.assertEqual(seconde.places.get().siege, self.siege)
