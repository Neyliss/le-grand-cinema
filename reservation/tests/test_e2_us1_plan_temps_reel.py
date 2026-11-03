"""E2-US1 : en tant que spectateur, je veux voir le plan de la salle avec les sièges libres,
afin de choisir mes places. Un test par critère d'acceptation de la carte Trello."""
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from outils_de_test.fabriques import creer_seance, vendre
from reservation.services import creer_reservation


def statuts(plan):
    return {s["id"]: s for r in plan["rangees"] for s in r["sieges"]}


class PlanTempsReelTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        self.url_json = reverse("reservation:api_plan", args=[self.seance.id])

    def test_critere_1_un_siege_vendu_au_guichet_disparait_du_plan_en_moins_de_5_secondes(self):
        reservation = vendre(self.seance)  # vente au guichet
        siege = reservation.places.get().siege_id

        self.assertLessEqual(settings.RAFRAICHISSEMENT_PLAN_SECONDES, 5)  # le plan est relu toutes les 5 s au plus
        plan = self.client.get(self.url_json).json()
        self.assertEqual(statuts(plan)[siege]["statut"], "vendue")
        self.assertEqual(self.client.get(self.url_json)["Cache-Control"].count("no-cache"), 1)

    def test_critere_2_chaque_siege_montre_son_etat_explique_par_une_legende(self):
        vendre(self.seance)
        autres = list(self.seance.salle.sieges.values_list("id", flat=True)[5:7])
        creer_reservation(self.seance, autres)  # deux sièges bloqués par un autre spectateur

        plan = statuts(self.client.get(self.url_json).json())
        self.assertEqual({s["statut"] for s in plan.values()}, {"libre", "bloquee", "vendue"})
        self.assertIn("pmr", {s["type"] for s in plan.values()})
        page = self.client.get(reverse("reservation:plan", args=[self.seance.id]))
        for libelle in ("Libre", "Vendue", "Bloquée", "Place PMR"):
            self.assertContains(page, libelle)

    def test_critere_3_le_plan_se_lit_et_s_utilise_sur_un_telephone(self):
        page = self.client.get(reverse("reservation:plan", args=[self.seance.id]))

        self.assertContains(page, 'name="viewport" content="width=device-width')
        self.assertContains(page, "data-indicateur-temps-reel")
        self.assertContains(page, "Connexion perdue")
