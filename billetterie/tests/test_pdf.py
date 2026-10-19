"""RG-07 : le PDF envoyé au spectateur contient une page par billet."""
from django.test import TestCase

from billetterie.services import pdf_billets
from outils_de_test.fabriques import creer_seance, vendre


class PdfTests(TestCase):
    def test_le_pdf_contient_une_page_par_billet(self):
        reservation = vendre(creer_seance(), nb=3)

        pdf = pdf_billets(reservation)

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page "), 3)
