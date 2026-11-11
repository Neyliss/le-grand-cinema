"""Hébergement dont le disque est effacé à chaque redémarrage (Render) : la base garde les films,
les affiches de la démonstration sont remises à leur place au démarrage suivant."""
import shutil
import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from catalogue.models import Film

MEDIA_TEMPORAIRE = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAIRE, COMPTES_DEMO_LOCAUX=True)
class AffichesApresRedemarrageTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAIRE, ignore_errors=True)

    def charger(self, *options):
        sortie = StringIO()
        call_command("charger_demo", *options, stdout=sortie)
        return sortie.getvalue()

    def test_les_affiches_effacees_sont_remises_au_demarrage(self):
        self.charger()
        film = Film.objects.exclude(affiche="").first()
        film.affiche.storage.delete(film.affiche.name)        # le disque a été effacé
        self.assertFalse(film.affiche.storage.exists(film.affiche.name))
        sortie = self.charger("--si-perime")                  # démarrage suivant
        self.assertIn("rien à recharger", sortie)
        self.assertTrue(film.affiche.storage.exists(film.affiche.name))
        self.assertEqual(Film.objects.count(), 3)             # les films ne sont pas recréés

    def test_une_affiche_presente_n_est_pas_dupliquee(self):
        self.charger()
        stockage = Film.objects.first().affiche.storage
        avant = sorted(stockage.listdir("affiches")[1])
        self.charger("--si-perime")
        apres = sorted(stockage.listdir("affiches")[1])
        self.assertEqual(avant, apres)
