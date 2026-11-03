"""E6-US1 : en tant qu'agent d'accueil, je veux vendre une place depuis le même outil, afin que le site
et le guichet partagent les mêmes sièges. Un test par critère d'acceptation de la carte Trello."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from billetterie.services import controler_billet
from catalogue.models import Tarif
from outils_de_test.fabriques import creer_agent, creer_seance
from paiement.models import Paiement
from reservation.models import PlaceSeance, Reservation
from reservation.services import creer_reservation, plan_de_salle


class VenteGuichetTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        self.siege = self.seance.salle.sieges.first()
        self.tarif = Tarif.objects.first()  # Plein, 10 €
        self.client.force_login(creer_agent())

    def vendre(self, mode="carte", **autres):
        return self.client.post(reverse("guichet:vendre", args=[self.seance.id]),
                                {"sieges": [self.siege.id], f"tarif_{self.siege.id}": self.tarif.id, "mode": mode, **autres})

    def test_critere_1_une_place_vendue_au_guichet_n_est_plus_proposee_en_ligne(self):
        self.vendre()
        statuts = {s["id"]: s["statut"] for r in plan_de_salle(self.seance)["rangees"] for s in r["sieges"]}
        self.assertEqual(statuts[self.siege.id], PlaceSeance.Statut.VENDUE)

    def test_critere_2_un_siege_bloque_en_ligne_ne_peut_pas_etre_vendu_au_guichet(self):
        creer_reservation(self.seance, [self.siege.id])  # un spectateur est en train de payer en ligne
        self.vendre()
        self.assertFalse(Reservation.objects.filter(canal=Reservation.Canal.GUICHET).exists())

    def test_critere_3_les_billets_du_guichet_s_impriment_et_se_controlent_comme_en_ligne(self):
        reponse = self.vendre()
        reservation = Reservation.objects.get()
        page = self.client.get(reponse.url)
        self.assertContains(page, "Imprimer les billets")
        billet = reservation.billets().get()
        self.assertEqual(controler_billet(billet.code_qr, self.seance)["resultat"], "valide")

    def test_en_especes_la_monnaie_a_rendre_est_calculee(self):
        reponse = self.vendre("especes", montant_recu="20")
        self.assertContains(self.client.get(reponse.url), "À rendre : 10,00 €")
        self.assertEqual(Paiement.objects.get().montant_recu, Decimal("20.00"))

    def test_une_somme_recue_insuffisante_annule_la_vente(self):
        self.vendre("especes", montant_recu="5")
        self.assertFalse(Paiement.objects.exists())
        self.assertEqual(self.seance.places.get(siege=self.siege).statut, PlaceSeance.Statut.LIBRE)
