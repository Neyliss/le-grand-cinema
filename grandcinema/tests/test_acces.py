"""
Droits d'accès (grandcinema/acces.py) : le public n'entre pas dans les espaces du personnel,
et un agent d'accueil n'accède pas au pilotage réservé aux administrateurs.
Une redirection (302) renvoie vers la page de connexion.
"""
from django.test import TestCase
from django.urls import reverse

from outils_de_test.fabriques import creer_agent, creer_seance


class AccesDuPersonnelTests(TestCase):
    def test_guichet_interdit_au_public(self):
        self.assertEqual(self.client.get(reverse("guichet:tableau")).status_code, 302)

    def test_page_de_controle_reservee_au_personnel(self):
        url = reverse("controle:scanner", args=[creer_seance().id])
        self.assertEqual(self.client.get(url).status_code, 302)

        self.client.force_login(creer_agent())

        self.assertEqual(self.client.get(url).status_code, 200)

    def test_pilotage_interdit_aux_agents(self):
        self.client.force_login(creer_agent())

        self.assertEqual(self.client.get(reverse("pilotage:tableau")).status_code, 302)
