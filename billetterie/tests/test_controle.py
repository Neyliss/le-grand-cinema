"""E6-US2 et RG-08 : un billet ne permet d'entrer qu'une seule fois, pour sa séance."""
from django.test import TestCase

from billetterie.services import controler_billet
from outils_de_test.fabriques import creer_seance, reserver_avec_billets, vendre


class ControleTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()

    def test_billet_valide_puis_refuse_au_second_scan(self):
        billet = vendre(self.seance).billets().get()

        premier = controler_billet(billet.code_qr, self.seance)
        second = controler_billet(billet.code_qr, self.seance)

        self.assertEqual(premier["resultat"], "valide")
        self.assertEqual(second["resultat"], "deja_utilise")

    def test_billet_inconnu(self):
        self.assertEqual(controler_billet("faux-code", self.seance)["resultat"], "refuse")

    def test_billet_non_paye_refuse(self):
        billet = reserver_avec_billets(self.seance).billets().get()  # réservé, jamais payé

        self.assertEqual(controler_billet(billet.code_qr, self.seance)["resultat"], "refuse")

    def test_billet_d_une_autre_seance_refuse(self):
        billet = vendre(self.seance).billets().get()
        autre_seance = creer_seance()

        self.assertEqual(controler_billet(billet.code_qr, autre_seance)["titre"], "Mauvaise séance")
