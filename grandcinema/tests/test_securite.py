"""Sécurité avant la mise en ligne : essais de mots de passe limités, redirection après connexion,
comptes du personnel de la démonstration protégés en ligne."""
import os
import shutil
import tempfile
from io import StringIO
from unittest import mock

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from outils_de_test.fabriques import creer_spectateur

MOT_DE_PASSE = "Cinema-2026!"


@override_settings(CONNEXION_ESSAIS_MAX=3)
class EssaisDeConnexionTests(TestCase):
    def setUp(self):
        cache.clear()
        creer_spectateur("ada@exemple.fr", MOT_DE_PASSE)

    def tearDown(self):
        cache.clear()

    def test_trop_de_mots_de_passe_faux_bloquent_l_identifiant(self):
        for _ in range(3):
            self.assertIsNone(authenticate(username="ada@exemple.fr", password="faux"))
        # Même le bon mot de passe est refusé pendant le blocage
        self.assertIsNone(authenticate(username="ada@exemple.fr", password=MOT_DE_PASSE))

    def test_une_connexion_reussie_remet_le_compteur_a_zero(self):
        for _ in range(2):
            authenticate(username="ada@exemple.fr", password="faux")
        self.assertIsNotNone(authenticate(username="ada@exemple.fr", password=MOT_DE_PASSE))
        for _ in range(2):
            authenticate(username="ada@exemple.fr", password="faux")
        self.assertIsNotNone(authenticate(username="ada@exemple.fr", password=MOT_DE_PASSE))

    def test_la_page_de_connexion_explique_le_blocage(self):
        for _ in range(3):
            self.client.post(reverse("comptes:connexion"), {"email": "ada@exemple.fr", "mot_de_passe": "faux"})
        reponse = self.client.post(reverse("comptes:connexion"), {"email": "ada@exemple.fr", "mot_de_passe": MOT_DE_PASSE})
        self.assertContains(reponse, "réessayez dans 15 minutes")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_l_administration_est_aussi_protegee(self):
        User.objects.create_superuser("direction", "d@exemple.fr", MOT_DE_PASSE)
        for _ in range(3):
            self.client.post(reverse("admin:login"), {"username": "direction", "password": "faux"})
        self.client.post(reverse("admin:login"), {"username": "direction", "password": MOT_DE_PASSE})
        self.assertNotIn("_auth_user_id", self.client.session)


class RedirectionApresConnexionTests(TestCase):
    def setUp(self):
        cache.clear()
        creer_spectateur("ada@exemple.fr", MOT_DE_PASSE)

    def se_connecter(self, suite):
        return self.client.post(reverse("comptes:connexion") + "?next=" + suite,
                                {"email": "ada@exemple.fr", "mot_de_passe": MOT_DE_PASSE})

    def test_une_page_du_site_est_suivie(self):
        self.assertRedirects(self.se_connecter("/compte/abonnement/"), "/compte/abonnement/", fetch_redirect_response=False)

    def test_un_autre_site_est_refuse(self):
        for suite in ("//pirate.exemple", "/\\pirate.exemple", "https://pirate.exemple/"):
            with self.subTest(suite=suite):
                self.client.logout()
                self.assertRedirects(self.se_connecter(suite), reverse("comptes:mon_compte"), fetch_redirect_response=False)


MEDIA_TEMPORAIRE = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAIRE)
class ComptesDuPersonnelEnLigneTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAIRE, ignore_errors=True)

    def charger(self, *options):
        call_command("charger_demo", *options, stdout=StringIO())

    @override_settings(COMPTES_DEMO_LOCAUX=True)
    def test_en_local_les_mots_de_passe_du_readme_marchent(self):
        self.charger()
        self.assertTrue(User.objects.get(username="admin").check_password("admin-gc-2026"))
        self.assertTrue(User.objects.get(username="agent").check_password("agent-gc-2026"))

    @override_settings(COMPTES_DEMO_LOCAUX=False)
    def test_en_ligne_sans_mot_de_passe_choisi_les_comptes_sont_bloques(self):
        with mock.patch.dict(os.environ, {"MOT_DE_PASSE_DEMO": ""}):
            self.charger()
        for identifiant, publie in (("admin", "admin-gc-2026"), ("agent", "agent-gc-2026")):
            compte = User.objects.get(username=identifiant)
            self.assertFalse(compte.has_usable_password())
            self.assertFalse(compte.check_password(publie))

    @override_settings(COMPTES_DEMO_LOCAUX=False)
    def test_en_ligne_le_mot_de_passe_vient_de_la_console_aws(self):
        with mock.patch.dict(os.environ, {"MOT_DE_PASSE_DEMO": "Choisi-Dans-La-Console-42"}):
            self.charger()
        admin = User.objects.get(username="admin")
        self.assertTrue(admin.check_password("Choisi-Dans-La-Console-42"))
        self.assertFalse(admin.check_password("admin-gc-2026"))

    @override_settings(COMPTES_DEMO_LOCAUX=False)
    def test_un_nouveau_mot_de_passe_s_applique_au_deploiement_suivant(self):
        with mock.patch.dict(os.environ, {"MOT_DE_PASSE_DEMO": "Premier-Choix-42"}):
            self.charger()
        # Déploiement suivant : la programmation est à jour, seuls les mots de passe sont revus
        with mock.patch.dict(os.environ, {"MOT_DE_PASSE_DEMO": "Second-Choix-42"}):
            self.charger("--si-perime")
        self.assertTrue(User.objects.get(username="agent").check_password("Second-Choix-42"))
