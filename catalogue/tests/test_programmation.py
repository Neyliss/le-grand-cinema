"""E1-US1 : la programmation affiche les séances du jour et leurs places libres, sans compte."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from outils_de_test.fabriques import creer_seance
from reservation.services import annuler_seance


class ProgrammationTests(TestCase):
    def test_programmation_du_jour_avec_places_libres(self):
        seance = creer_seance(dans=timedelta(minutes=30))

        reponse = self.client.get(reverse("catalogue:programmation"))

        self.assertContains(reponse, "Film test")
        self.assertContains(reponse, timezone.localtime(seance.debut).strftime("%H:%M"))
        self.assertContains(reponse, "15 libres")

    def test_seance_annulee_retiree_de_la_programmation(self):
        seance = creer_seance(dans=timedelta(minutes=30))

        annuler_seance(seance)

        self.assertNotContains(self.client.get(reverse("catalogue:programmation")), "Film test")
