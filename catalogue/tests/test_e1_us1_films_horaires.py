"""E1-US1 : en tant que visiteur, je veux voir les films de la semaine avec leurs horaires,
afin de choisir une séance sans me déplacer. Un test par critère d'acceptation de la carte Trello."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from outils_de_test.fabriques import creer_seance, vendre
from reservation.services import annuler_seance


class FilmsEtHorairesTests(TestCase):
    def programmation(self, jour):
        return self.client.get(reverse("catalogue:programmation"), {"jour": jour.isoformat()})

    def test_critere_1_titre_duree_version_salle_et_horaire_filtrables_par_jour(self):
        demain = creer_seance(dans=timedelta(days=1))
        demain.film.titre = "Film de demain"
        demain.film.save()
        jour = timezone.localdate(demain.debut)

        reponse = self.programmation(jour)

        for attendu in ("Film de demain", "1 h 40", "VF", demain.salle.nom, timezone.localtime(demain.debut).strftime("%H:%M")):
            self.assertContains(reponse, attendu)
        self.assertNotContains(self.programmation(jour + timedelta(days=1)), "Film de demain")

    def test_critere_2_les_places_libres_tiennent_compte_des_ventes_du_guichet(self):
        seance = creer_seance(dans=timedelta(days=1))
        vendre(seance, nb=3)  # 15 places, dont 3 vendues au guichet

        self.assertContains(self.programmation(timezone.localdate(seance.debut)), "12 libres")

    def test_critere_3_une_seance_commencee_ou_annulee_n_apparait_plus(self):
        commencee = creer_seance(dans=-timedelta(minutes=5))
        annulee = creer_seance(dans=timedelta(days=1))
        annuler_seance(annulee)

        self.assertNotContains(self.programmation(timezone.localdate(commencee.debut)), "Film test")
        self.assertNotContains(self.programmation(timezone.localdate(annulee.debut)), "Film test")
