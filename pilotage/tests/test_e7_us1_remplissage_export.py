"""E7-US1 : en tant qu'administrateur, je veux voir le remplissage par séance et l'exporter, afin de
repérer les séances faibles et les créneaux saturés. Un test par critère d'acceptation de la carte Trello."""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from outils_de_test.fabriques import creer_administrateur, creer_seance, reserver_avec_billets, vendre
from paiement.models import Paiement
from paiement.services import confirmer_paiement


class RemplissageExportTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        vendre(self.seance, nb=3)  # guichet
        en_ligne = reserver_avec_billets(self.seance, nb=1)
        confirmer_paiement(en_ligne.id, Paiement.Mode.CARTE_EN_LIGNE)  # site
        jour = timezone.localdate(self.seance.debut)
        self.periode = {"du": jour, "au": jour}
        self.client.force_login(creer_administrateur())

    def test_critere_1_tableau_a_jour_en_temps_reel_et_exportable_en_csv(self):
        page = self.client.get(reverse("pilotage:tableau"), self.periode)
        self.assertEqual(page.context["indicateurs"]["vendues"], 4)
        self.assertContains(page, 'http-equiv="refresh"')

        export = self.client.get(reverse("pilotage:export_csv"), self.periode)
        self.assertEqual(export["Content-Type"], "text/csv; charset=utf-8")

    def test_critere_2_les_ventes_du_site_et_du_guichet_sont_separees_pour_suivre_o1(self):
        page = self.client.get(reverse("pilotage:tableau"), self.periode)
        ligne = page.context["lignes"][0]
        self.assertEqual((ligne["vendues_site"], ligne["vendues_guichet"]), (1, 3))
        self.assertEqual(page.context["indicateurs"]["part_site"], 25)
        self.assertContains(page, "Objectif 50 % · pas encore atteint")

    def test_critere_3_chaque_ligne_de_l_export_indique_la_date_et_l_heure(self):
        lignes = self.client.get(reverse("pilotage:export_csv"), self.periode).content.decode("utf-8-sig").splitlines()
        debut = timezone.localtime(self.seance.debut)
        self.assertTrue(lignes[1].startswith(f"{debut:%d/%m/%Y};{debut:%H:%M};"))
