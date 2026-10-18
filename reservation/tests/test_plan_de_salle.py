"""RG-09 et RG-11 : le plan de salle donne l'état réel des sièges ; une séance passée n'est plus réservable."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse

from outils_de_test.fabriques import creer_seance
from reservation.services import creer_reservation, plan_de_salle


class PlanDeSalleTests(TestCase):
    def test_le_plan_json_indique_le_statut_de_chaque_siege(self):
        seance = creer_seance()
        siege = seance.salle.sieges.first()
        creer_reservation(seance, [siege.id])

        reponse = self.client.get(reverse("reservation:api_plan", args=[seance.id]))

        self.assertEqual(reponse.status_code, 200)
        donnees = reponse.json()
        statuts = {s["id"]: s["statut"] for r in donnees["rangees"] for s in r["sieges"]}
        self.assertEqual(statuts[siege.id], "bloquee")
        self.assertEqual(donnees["libres"], 14)
        self.assertEqual(donnees["allees"], [2])

    def test_seance_passee_non_reservable(self):
        seance = creer_seance(dans=-timedelta(hours=1))

        reponse = self.client.post(reverse("reservation:bloquer", args=[seance.id]),
                                   {"sieges": [seance.salle.sieges.first().id]})

        self.assertFalse(plan_de_salle(seance)["reservable"])
        self.assertRedirects(reponse, reverse("catalogue:programmation"))
