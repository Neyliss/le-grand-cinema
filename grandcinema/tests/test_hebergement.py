"""Hébergement dont le disque est effacé à chaque redémarrage (Render) : la base garde les films,
les affiches de la démonstration sont remises à leur place au démarrage suivant."""
import shutil
import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from catalogue.models import Film


@override_settings(COMPTES_DEMO_LOCAUX=True)
class AffichesApresRedemarrageTests(TestCase):
    def setUp(self):
        # Un dossier d'images neuf pour chaque test : l'ordre des tests (aléatoire) ne compte pas
        dossier = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, dossier, True)
        reglage = override_settings(MEDIA_ROOT=dossier)
        reglage.enable()
        self.addCleanup(reglage.disable)

    def charger(self, *options):
        sortie = StringIO()
        call_command("charger_demo", *options, stdout=sortie)
        return sortie.getvalue()

    def effacer_une_affiche(self):
        film = Film.objects.exclude(affiche="").first()
        film.affiche.storage.delete(film.affiche.name)        # le disque a été effacé
        self.assertFalse(film.affiche.storage.exists(film.affiche.name))
        return film

    def test_les_affiches_effacees_sont_remises_au_demarrage(self):
        self.charger()
        film = self.effacer_une_affiche()
        sortie = self.charger("--si-perime")                  # démarrage suivant
        self.assertIn("rien à recharger", sortie)
        self.assertTrue(film.affiche.storage.exists(film.affiche.name))
        self.assertEqual(Film.objects.count(), 3)             # les films ne sont pas recréés

    def test_une_affiche_renommee_par_django_est_aussi_remise(self):
        self.charger()
        self.charger("--reinitialiser")                       # les fichiers existent : Django les renomme
        film = self.effacer_une_affiche()
        self.assertRegex(film.affiche.name, r"_[A-Za-z0-9]{7}\.png$")
        self.charger("--si-perime")
        self.assertTrue(film.affiche.storage.exists(film.affiche.name))

    def test_une_affiche_presente_n_est_pas_dupliquee(self):
        self.charger()
        stockage = Film.objects.first().affiche.storage
        avant = sorted(stockage.listdir("affiches")[1])
        self.charger("--si-perime")
        apres = sorted(stockage.listdir("affiches")[1])
        self.assertEqual(avant, apres)

class ReglagesSelonHebergeurTests(TestCase):
    def test_aws_par_defaut(self):
        from grandcinema.hebergement import adresse_publique, entete_https, hotes_autorises
        aws = {"SITE_URL": "https://d1abc.cloudfront.net"}
        self.assertEqual(entete_https(aws), ("HTTP_CLOUDFRONT_FORWARDED_PROTO", "https"))
        self.assertEqual(adresse_publique(aws), "https://d1abc.cloudfront.net")
        self.assertEqual(hotes_autorises([".cloudfront.net"], aws), [".cloudfront.net"])

    def test_render(self):
        from grandcinema.hebergement import adresse_publique, entete_https, hotes_autorises
        render = {"PROXY_HTTPS": "standard", "RENDER_EXTERNAL_HOSTNAME": "gc.onrender.com",
                  "RENDER_EXTERNAL_URL": "https://gc.onrender.com"}
        self.assertEqual(entete_https(render), ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertEqual(adresse_publique(render), "https://gc.onrender.com")
        self.assertEqual(hotes_autorises(["localhost"], render), ["localhost", "gc.onrender.com"])

    def test_en_local_sans_reglage(self):
        from grandcinema.hebergement import adresse_publique
        self.assertEqual(adresse_publique({}), "http://127.0.0.1:8000")
