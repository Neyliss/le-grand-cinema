"""E5-US2 : en tant qu'administrateur, je veux annuler une séance, afin de corriger la programmation.
Un test par critère d'acceptation de la carte Trello."""
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from catalogue.models import Seance
from outils_de_test.fabriques import creer_administrateur, creer_seance, vendre
from paiement.models import Paiement


class AnnulerSeanceTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        self.reservation = vendre(self.seance, nb=2)
        self.reservation.email = "spectateur@exemple.fr"
        self.reservation.save(update_fields=["email"])
        self.client.force_login(creer_administrateur())

    def annuler_depuis_l_administration(self):
        return self.client.post(reverse("admin:catalogue_seance_changelist"),
                                {"action": "annuler", "_selected_action": [self.seance.id]}, follow=True)

    def test_critere_1_les_spectateurs_sont_prevenus_par_email_et_rembourses(self):
        self.annuler_depuis_l_administration()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["spectateur@exemple.fr"])
        self.assertIn("autre séance", mail.outbox[0].body)
        self.assertEqual(Paiement.objects.get(reservation=self.reservation).statut, Paiement.Statut.REMBOURSE)

    def test_critere_2_la_seance_disparait_du_site_et_n_est_plus_reservable(self):
        self.annuler_depuis_l_administration()

        self.seance.refresh_from_db()
        self.assertEqual(self.seance.statut, Seance.Statut.ANNULEE)
        self.assertNotContains(self.client.get(reverse("catalogue:programmation")), "Film test")
        self.assertEqual(self.client.get(reverse("reservation:plan", args=[self.seance.id])).status_code, 404)
