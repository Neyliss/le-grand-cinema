"""E1-US2 : le site existe en anglais, et l'on peut passer d'une langue à l'autre dans les deux sens."""
from datetime import timedelta

from django.conf import settings
from django.test import TestCase
from django.utils import translation

from outils_de_test.fabriques import creer_seance


class LanguesTests(TestCase):
    def tearDown(self):
        # Une page /en/ laisse l'anglais actif pour la suite du programme de test.
        # On remet le français pour que les tests suivants ne dépendent pas de celui-ci.
        translation.activate(settings.LANGUAGE_CODE)

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
