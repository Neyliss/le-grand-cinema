"""Pilotage (E7-US1) : remplissage par séance, exportable au format CSV."""
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from billetterie.tests import vendre
from grandcinema.acces import GROUPE_ADMINISTRATEURS
from reservation.tests import creer_seance


class PilotageTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        vendre(self.seance, nb=3)
        admin = User.objects.create_user("direction", password="x", is_staff=True)
        admin.groups.add(Group.objects.create(name=GROUPE_ADMINISTRATEURS))
        self.client.force_login(admin)

    def test_tableau_de_remplissage(self):
        jour = timezone.localdate(self.seance.debut)
        reponse = self.client.get(reverse("pilotage:tableau"), {"du": jour, "au": jour})
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.context["indicateurs"]["vendues"], 3)
        self.assertEqual(reponse.context["indicateurs"]["taux"], 20)  # 3 places sur 15

    def test_export_csv(self):
        jour = timezone.localdate(self.seance.debut)
        reponse = self.client.get(reverse("pilotage:export_csv"), {"du": jour, "au": jour})
        contenu = reponse.content.decode("utf-8-sig").splitlines()
        self.assertTrue(contenu[0].startswith("Date;Heure;Film"))
        self.assertIn(";3;", contenu[1])

    def test_pilotage_interdit_aux_agents(self):
        self.client.force_login(User.objects.create_user("agent", password="x", is_staff=True))
        self.assertEqual(self.client.get(reverse("pilotage:tableau")).status_code, 302)
