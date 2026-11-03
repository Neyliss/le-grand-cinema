"""E4-US1 : en tant que spectateur, je veux recevoir mon billet par e-mail, afin de le présenter
sur mon téléphone. Un test par critère d'acceptation de la carte Trello."""
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from billetterie.views import RENVOIS_MAX
from outils_de_test.fabriques import creer_seance, reserver_avec_billets
from paiement.models import Paiement
from paiement.services import confirmer_paiement


class BilletParEmailTests(TestCase):
    def setUp(self):
        self.reservation = reserver_avec_billets(creer_seance(), nb=3)
        self.reservation.email = "ada@exemple.fr"
        self.reservation.save(update_fields=["email"])
        with self.captureOnCommitCallbacks(execute=True):  # comme en production, juste après le paiement
            confirmer_paiement(self.reservation.id, Paiement.Mode.CARTE_EN_LIGNE)
        self.url = reverse("billetterie:billet", args=[self.reservation.reference, self.reservation.jeton])

    def test_critere_1_le_billet_pdf_avec_un_qr_code_unique_part_juste_apres_le_paiement(self):
        self.assertEqual(len(mail.outbox), 1)  # envoyé immédiatement, sans attente
        piece_jointe = mail.outbox[0].attachments[0]
        self.assertTrue(piece_jointe[0].endswith(".pdf"))
        codes = [b.code_qr for b in self.reservation.billets()]
        self.assertEqual(len(set(codes)), 3)

    def test_critere_2_le_pdf_contient_un_billet_par_place(self):
        pdf = mail.outbox[0].attachments[0][1]
        self.assertEqual(pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page "), 3)

    def test_critere_3_les_billets_s_affichent_aussi_sur_la_page_de_confirmation(self):
        page = self.client.get(self.url)
        self.assertEqual(page.content.count(b'class="billet__qr"'), 3)

    def test_le_spectateur_peut_se_renvoyer_son_billet_trois_fois_au_plus(self):
        url = reverse("billetterie:renvoyer", args=[self.reservation.reference, self.reservation.jeton])
        for _ in range(RENVOIS_MAX + 1):
            self.client.post(url)
        self.assertEqual(len(mail.outbox), 1 + RENVOIS_MAX)
