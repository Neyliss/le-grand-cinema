"""API du compte spectateur : mêmes règles que le site, documentées dans Swagger (/api/docs/)."""
import re

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from outils_de_test.fabriques import acheter_en_ligne, creer_seance, creer_spectateur

MOT_DE_PASSE = "Cinema-2026!"


class ApiCompteTests(TestCase):
    def setUp(self):
        cache.clear()  # remet à zéro le compteur de la limite de requêtes
        self.api = APIClient()

    def tearDown(self):
        cache.clear()  # les mots de passe faux de ces tests ne bloquent pas les tests suivants

    def obtenir_jeton(self, email="ada@exemple.fr", mot_de_passe=MOT_DE_PASSE):
        return self.api.post("/api/comptes/jeton/", {"email": email, "mot_de_passe": mot_de_passe}, format="json")

    def test_parcours_complet_creer_confirmer_se_connecter_consulter_supprimer(self):
        reservation = acheter_en_ligne(creer_seance(), "ada@exemple.fr", nb=2)

        with self.captureOnCommitCallbacks(execute=True):
            creation = self.api.post("/api/comptes/", {"nom": "Ada", "email": "ada@exemple.fr", "mot_de_passe": MOT_DE_PASSE}, format="json")
        self.assertEqual(creation.status_code, 201)
        self.assertEqual(self.obtenir_jeton().status_code, 400)  # adresse pas encore confirmée

        jeton_email = re.search(r"/compte/confirmer/(\S+)/", mail.outbox[-1].body).group(1)
        self.assertEqual(self.api.post("/api/comptes/confirmer/", {"jeton": jeton_email}, format="json").status_code, 200)

        jeton = self.obtenir_jeton().json()["jeton"]
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {jeton}")
        self.assertEqual(self.api.get("/api/comptes/moi/").json(), {"email": "ada@exemple.fr", "nom": "Ada", "email_confirme": True})
        reservations = self.api.get("/api/comptes/moi/reservations/").json()
        self.assertEqual([(r["reference"], r["nombre_de_places"], r["statut"]) for r in reservations],
                         [(reservation.reference, 2, "payee")])

        self.assertEqual(self.api.delete("/api/comptes/moi/").status_code, 204)
        self.assertFalse(User.objects.filter(email="ada@exemple.fr").exists())
        self.assertEqual(self.api.get("/api/comptes/moi/").status_code, 401)  # le jeton est supprimé avec le compte

    def test_les_routes_moi_demandent_un_jeton(self):
        self.assertEqual(self.api.get("/api/comptes/moi/").status_code, 401)
        self.assertEqual(self.api.get("/api/comptes/moi/reservations/").status_code, 401)
        self.api.credentials(HTTP_AUTHORIZATION="Token faux-jeton")
        self.assertEqual(self.api.get("/api/comptes/moi/").status_code, 401)

    def test_erreurs_claires_adresse_deja_prise_mot_de_passe_faible_ou_faux(self):
        creer_spectateur()

        deja_pris = self.api.post("/api/comptes/", {"nom": "Ada", "email": "ada@exemple.fr", "mot_de_passe": MOT_DE_PASSE}, format="json")
        trop_faible = self.api.post("/api/comptes/", {"nom": "Bob", "email": "bob@exemple.fr", "mot_de_passe": "1234"}, format="json")

        self.assertEqual(deja_pris.status_code, 409)
        self.assertEqual(trop_faible.status_code, 400)
        self.assertIn("mot_de_passe", trop_faible.json())
        self.assertEqual(self.obtenir_jeton(mot_de_passe="mauvais").status_code, 400)

    def test_trop_d_essais_de_connexion_sont_bloques(self):
        creer_spectateur()

        codes = [self.obtenir_jeton(mot_de_passe="mauvais").status_code for _ in range(21)]

        self.assertEqual(codes[-1], 429)  # au-delà de 20 essais par minute

    def test_la_documentation_swagger_est_en_ligne(self):
        self.assertEqual(self.client.get("/api/docs/").status_code, 200)
        schema = self.client.get("/api/schema/", HTTP_ACCEPT="application/json").json()
        self.assertIn("/api/comptes/moi/reservations/", schema["paths"])
