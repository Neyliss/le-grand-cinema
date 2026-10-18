"""À la création d'une séance, chaque siège de la salle devient une place libre."""
from django.test import TestCase

from outils_de_test.fabriques import creer_seance
from reservation.models import PlaceSeance


class GenerationDesPlacesTests(TestCase):
    def test_une_place_libre_par_siege_a_la_creation_de_la_seance(self):
        seance = creer_seance()  # salle de 3 rangées de 5 sièges

        self.assertEqual(seance.places.count(), 15)
        self.assertTrue(all(p.statut == PlaceSeance.Statut.LIBRE for p in seance.places.all()))

    def test_sieges_pmr_sur_la_derniere_rangee(self):
        seance = creer_seance()

        pmr = seance.salle.sieges.filter(type="pmr")

        self.assertEqual([str(s) for s in pmr], ["C1", "C2"])
