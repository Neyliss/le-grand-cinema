"""Chaque réservation a une référence unique : elle est imprimée sur les billets et donnée au guichet."""
from django.test import TestCase

from outils_de_test.fabriques import creer_seance
from reservation.models import Reservation


class ReferenceUniqueTests(TestCase):
    def test_une_reference_deja_prise_est_remplacee(self):
        # Préparer : une première réservation et sa référence
        seance = creer_seance()
        premiere = Reservation.objects.create(seance=seance)

        # Agir : une seconde réservation tombe sur la même référence
        seconde = Reservation.objects.create(seance=seance, reference=premiere.reference)

        # Vérifier : elle reçoit une autre référence, au même format
        self.assertNotEqual(seconde.reference, premiere.reference)
        self.assertRegex(seconde.reference, r"^GC-[A-Z2-9]{5}$")
