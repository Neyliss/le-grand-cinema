"""Pages publiques (E1) : programmation sans compte, en français et en anglais."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from reservation.services import annuler_seance
from reservation.tests import creer_seance


class ProgrammationTests(TestCase):
    def test_programmation_du_jour_avec_places_libres(self):
        seance = creer_seance(dans=timedelta(minutes=30))
        reponse = self.client.get(reverse("catalogue:programmation"))
        self.assertContains(reponse, "Film test")
        self.assertContains(reponse, timezone.localtime(seance.debut).strftime("%H:%M"))
        self.assertContains(reponse, "15 libres")

    def test_site_en_anglais(self):
        creer_seance(dans=timedelta(minutes=30))
        reponse = self.client.get("/en/")
        self.assertContains(reponse, "Showtimes")
        self.assertContains(reponse, "15 seats available")

    def test_on_peut_passer_en_anglais_puis_revenir_en_francais(self):
        # En français, le bouton EN mène à la même page en anglais…
        reponse = self.client.get("/infos/?onglet=tarifs")
        self.assertContains(reponse, '<html lang="fr">')
        self.assertContains(reponse, 'href="/en/infos/?onglet=tarifs"')
        # … et en anglais, le bouton FR ramène à la page en français.
        reponse = self.client.get("/en/infos/?onglet=tarifs")
        self.assertContains(reponse, '<html lang="en">')
        self.assertContains(reponse, 'href="/infos/?onglet=tarifs"')
        # Après un passage en anglais, la page française reste bien en français.
        self.assertContains(self.client.get("/infos/"), '<html lang="fr">')

    def test_seance_annulee_retiree_de_la_programmation(self):
        seance = creer_seance(dans=timedelta(minutes=30))
        annuler_seance(seance)
        self.assertNotContains(self.client.get(reverse("catalogue:programmation")), "Film test")
