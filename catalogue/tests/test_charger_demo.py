"""Commande charger_demo : les données de démonstration utilisées par Docker et pour la soutenance."""
import shutil
import tempfile
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings

from billetterie.models import Billet
from catalogue.models import Film, Salle, Seance
from grandcinema.acces import GROUPE_ADMINISTRATEURS, GROUPE_AGENTS
from reservation.models import PlaceSeance

MEDIA_TEMPORAIRE = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAIRE)
class ChargerDemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("charger_demo", stdout=StringIO())

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAIRE, ignore_errors=True)

    def test_le_cinema_de_demonstration_a_10_salles_et_1700_places(self):
        self.assertEqual(Salle.objects.count(), 10)
        self.assertEqual(sum(salle.sieges.count() for salle in Salle.objects.all()), 1700)
        self.assertEqual(Film.objects.count(), 3)
        self.assertEqual(Seance.objects.count(), 7 * 7)

    def test_des_billets_sont_deja_vendus_sur_les_places_vendues(self):
        vendues = PlaceSeance.objects.filter(statut=PlaceSeance.Statut.VENDUE).count()

        self.assertGreater(vendues, 0)
        self.assertEqual(Billet.objects.count(), vendues)

    def test_les_deux_comptes_du_personnel_sont_crees(self):
        admin = User.objects.get(username="admin")
        agent = User.objects.get(username="agent")

        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.groups.filter(name=GROUPE_ADMINISTRATEURS).exists())
        self.assertTrue(agent.groups.filter(name=GROUPE_AGENTS).exists())
        self.assertFalse(agent.is_superuser)

    def test_un_second_lancement_ne_duplique_rien(self):
        sortie = StringIO()

        call_command("charger_demo", stdout=sortie)

        self.assertIn("--reinitialiser", sortie.getvalue())
        self.assertEqual(Film.objects.count(), 3)

    def test_reinitialiser_recharge_les_donnees(self):
        call_command("charger_demo", "--reinitialiser", stdout=StringIO())

        self.assertEqual(Film.objects.count(), 3)
        self.assertEqual(Seance.objects.count(), 7 * 7)
