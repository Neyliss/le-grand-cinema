"""API publique de la programmation : mêmes données que les pages, lisibles sans compte."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from catalogue.models import Seance
from outils_de_test.fabriques import creer_seance, vendre


class ApiProgrammationTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()  # demain, 15 places

    def test_les_seances_d_un_jour_avec_leurs_places_libres(self):
        vendre(self.seance, nb=3)
        creer_seance(dans=timedelta(days=3))  # un autre jour : absente du résultat
        jour = timezone.localdate(self.seance.debut).isoformat()

        reponse = self.client.get("/api/seances/", {"jour": jour})

        self.assertEqual(reponse.status_code, 200)
        self.assertEqual([(s["id"], s["places_libres"]) for s in reponse.json()], [(self.seance.id, 12)])

    def test_une_seance_annulee_ou_deja_commencee_n_est_pas_proposee(self):
        Seance.objects.filter(pk=self.seance.pk).update(statut=Seance.Statut.ANNULEE)
        Seance.objects.create(film=self.seance.film, salle=self.seance.salle, debut=timezone.now() - timedelta(hours=1))

        self.assertEqual(self.client.get("/api/seances/").json(), [])
        self.assertEqual(self.client.get("/api/films/").json(), [])

    def test_le_plan_de_salle_montre_les_sieges_vendus(self):
        vendre(self.seance, nb=2)

        plan = self.client.get(f"/api/seances/{self.seance.id}/plan/").json()

        statuts = [s["statut"] for r in plan["rangees"] for s in r["sieges"]]
        self.assertEqual((statuts.count("vendue"), plan["libres"]), (2, 13))

    def test_une_date_mal_ecrite_renvoie_une_erreur_claire(self):
        reponse = self.client.get("/api/seances/", {"jour": "05/11/2026"})

        self.assertEqual(reponse.status_code, 400)
        self.assertIn("jour", reponse.json())

    def test_les_films_a_l_affiche(self):
        self.assertEqual([f["titre"] for f in self.client.get("/api/films/").json()], ["Film test"])
