"""Contrôle à l'entrée (E6-US2) : un billet déjà scanné est refusé avec un message clair."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from catalogue.models import Tarif
from paiement.models import Paiement
from paiement.services import confirmer_paiement
from reservation.services import creer_reservation
from reservation.tests import creer_seance

from .services import controler_billet, creer_billets, pdf_billets


def vendre(seance, nb=1):
    reservation = creer_reservation(seance, [s.id for s in seance.salle.sieges.all()[:nb]])
    tarif = Tarif.objects.first()
    creer_billets(reservation, {p.id: tarif for p in reservation.places.all()})
    confirmer_paiement(reservation.id, Paiement.Mode.GUICHET_CARTE)
    return reservation


class ControleTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()

    def test_billet_valide_puis_refuse_au_second_scan(self):
        billet = vendre(self.seance).billets().get()
        self.assertEqual(controler_billet(billet.code_qr, self.seance)["resultat"], "valide")
        self.assertEqual(controler_billet(billet.code_qr, self.seance)["resultat"], "deja_utilise")

    def test_billet_inconnu(self):
        self.assertEqual(controler_billet("faux-code", self.seance)["resultat"], "refuse")

    def test_billet_non_paye_refuse(self):
        reservation = creer_reservation(self.seance, [self.seance.salle.sieges.first().id])
        creer_billets(reservation, {p.id: Tarif.objects.first() for p in reservation.places.all()})
        billet = reservation.billets().get()
        self.assertEqual(controler_billet(billet.code_qr, self.seance)["resultat"], "refuse")

    def test_billet_d_une_autre_seance_refuse(self):
        billet = vendre(self.seance).billets().get()
        autre = creer_seance()
        self.assertEqual(controler_billet(billet.code_qr, autre)["titre"], "Mauvaise séance")

    def test_page_de_controle_reservee_au_personnel(self):
        url = reverse("controle:scanner", args=[self.seance.id])
        self.assertEqual(self.client.get(url).status_code, 302)
        agent = User.objects.create_user("agent", password="x", is_staff=True)
        self.client.force_login(agent)
        self.assertEqual(self.client.get(url).status_code, 200)


class PdfTests(TestCase):
    def test_le_pdf_contient_une_page_par_billet(self):
        reservation = vendre(creer_seance(), nb=3)
        pdf = pdf_billets(reservation)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page "), 3)
