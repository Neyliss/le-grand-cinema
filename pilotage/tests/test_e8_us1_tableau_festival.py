"""E8-US1 : en tant qu'administrateur, je veux voir à l'avance les séances du festival qui vont être complètes,
afin d'ouvrir des séances supplémentaires à temps. Un test par critère d'acceptation de la carte Trello."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from outils_de_test.fabriques import creer_administrateur, creer_seance, vendre
from paiement.models import Paiement
from pilotage.views import ventes_festival


def seance_du_festival(dans):
    seance = creer_seance(dans=dans)  # 15 places
    seance.film.festival = True
    seance.film.save()
    return seance


class TableauFestivalTests(TestCase):
    def setUp(self):
        self.client.force_login(creer_administrateur())

    def test_critere_1_les_places_vendues_jour_apres_jour_depuis_l_ouverture_des_ventes(self):
        seance = seance_du_festival(timedelta(days=10))
        il_y_a_deux_jours = vendre(seance, nb=2)
        Paiement.objects.filter(reservation=il_y_a_deux_jours).update(cree_le=timezone.now() - timedelta(days=2))
        vendre(seance, nb=3)  # aujourd'hui

        lignes, jours = ventes_festival()

        self.assertEqual(len(jours), 3)  # avant-hier, hier, aujourd'hui
        self.assertEqual([p["cumul"] for p in lignes[0]["courbe"]], [2, 2, 5])
        self.assertContains(self.client.get(reverse("pilotage:festival")), "5 / 15")

    def test_critere_2_une_seance_remplie_a_80_pour_cent_trois_jours_avant_est_signalee(self):
        bientot_pleine = seance_du_festival(timedelta(days=2))
        vendre(bientot_pleine, nb=6), vendre(bientot_pleine, nb=6)  # 12 / 15 = 80 % (8 places au plus par vente)
        lointaine = seance_du_festival(timedelta(days=20))
        vendre(lointaine, nb=6), vendre(lointaine, nb=6)  # 80 % aussi, mais encore loin : pas d'alerte

        alertes = {l["seance"].id: l["alerte"] for l in ventes_festival()[0]}

        self.assertEqual(alertes, {bientot_pleine.id: True, lointaine.id: False})
        self.assertContains(self.client.get(reverse("pilotage:festival")), "1 séance à surveiller")

    def test_critere_3_les_donnees_sont_disponibles_au_moins_4_semaines_avant_le_festival(self):
        dans_six_semaines = seance_du_festival(timedelta(weeks=6))

        self.assertIn(dans_six_semaines.id, [l["seance"].id for l in ventes_festival()[0]])

    def test_le_tableau_du_festival_est_reserve_aux_administrateurs(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("pilotage:festival")).status_code, 302)
