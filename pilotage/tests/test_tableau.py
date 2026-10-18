"""E7-US1 : le remplissage par séance est affiché et exportable au format CSV."""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from outils_de_test.fabriques import creer_administrateur, creer_seance, vendre


class TableauDeBordTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        vendre(self.seance, nb=3)  # 3 places vendues sur 15
        jour = timezone.localdate(self.seance.debut)
        self.periode = {"du": jour, "au": jour}
        self.client.force_login(creer_administrateur())

    def test_tableau_de_remplissage(self):
        reponse = self.client.get(reverse("pilotage:tableau"), self.periode)

        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.context["indicateurs"]["vendues"], 3)
        self.assertEqual(reponse.context["indicateurs"]["taux"], 20)  # 3 places sur 15

    def test_export_csv(self):
        reponse = self.client.get(reverse("pilotage:export_csv"), self.periode)

        lignes = reponse.content.decode("utf-8-sig").splitlines()
        self.assertTrue(lignes[0].startswith("Date;Heure;Film"))
        self.assertIn(";3;", lignes[1])
