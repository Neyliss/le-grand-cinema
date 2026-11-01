"""E6-US2 : en tant qu'agent d'accueil, je veux scanner un billet à l'entrée, afin de vérifier qu'il est
valide. Un test par critère d'acceptation de la carte Trello."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from outils_de_test.fabriques import creer_agent, creer_seance, reserver_avec_billets, vendre


class ControleBilletsTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        self.billet = vendre(self.seance).billets().get()
        self.client.force_login(creer_agent())

    def scanner(self, code, seance=None, action="verifier"):
        return self.client.post(reverse(f"controle:{action}", args=[(seance or self.seance).id]), {"code": code}).json()

    def test_critere_1_un_billet_deja_scanne_est_refuse_avec_un_message_clair(self):
        self.assertEqual(self.scanner(self.billet.code_qr)["resultat"], "valide")
        second = self.scanner(self.billet.code_qr)
        self.assertEqual(second["resultat"], "deja_utilise")
        self.assertIn("entrée refusée", second["detail"])

    def test_critere_2_billet_inconnu_non_paye_ou_d_une_autre_seance_refuse(self):
        non_paye = reserver_avec_billets(self.seance, nb=1).billets().get()
        autre_seance = creer_seance()

        self.assertEqual(self.scanner("CODE-INCONNU")["titre"], "Billet inconnu")
        self.assertEqual(self.scanner(non_paye.code_qr)["titre"], "Billet non valable")
        self.assertEqual(self.scanner(self.billet.code_qr, autre_seance)["titre"], "Mauvaise séance")

    def test_critere_3_seuls_les_agents_connectes_ouvrent_l_ecran_de_controle(self):
        self.client.logout()
        reponse = self.client.get(reverse("controle:scanner", args=[self.seance.id]))
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("/admin/login/", reponse.url)

    def test_l_agent_peut_annuler_une_entree_scannee_par_erreur(self):
        self.scanner(self.billet.code_qr)
        annulation = self.scanner(self.billet.code_qr, action="annuler")

        self.assertEqual(annulation["resultat"], "annule")
        self.assertEqual(annulation["compteur"]["entrees"], 0)
        self.assertEqual(self.scanner(self.billet.code_qr)["resultat"], "valide")  # de nouveau valable

    def test_une_entree_ancienne_de_plus_de_10_minutes_ne_s_annule_plus(self):
        self.scanner(self.billet.code_qr)
        self.billet.refresh_from_db()
        self.billet.utilise_le = timezone.now() - timedelta(minutes=11)
        self.billet.save(update_fields=["utilise_le"])

        self.assertEqual(self.scanner(self.billet.code_qr, action="annuler")["titre"], "Annulation impossible")
