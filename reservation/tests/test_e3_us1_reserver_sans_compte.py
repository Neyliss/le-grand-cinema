"""E3-US1 : en tant que touriste, je veux réserver sans créer de compte, afin d'aller vite.
Un test par critère d'acceptation de la carte Trello."""
from django.test import TestCase
from django.urls import reverse

from catalogue.models import Tarif
from outils_de_test.fabriques import creer_seance
from reservation.models import Reservation


class ReserverSansCompteTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        sieges = [s.id for s in self.seance.salle.sieges.all()[:2]]
        self.client.post(reverse("reservation:bloquer", args=[self.seance.id]), {"sieges": sieges})
        self.reservation = Reservation.objects.get()
        self.url = reverse("reservation:recapitulatif", args=[self.reservation.reference])

    def donnees(self, **autres):
        tarif = {f"tarif_{p.id}": str(Tarif.objects.get().id) for p in self.reservation.places.all()}
        return {**tarif, "nom": "Ada", "email": "ada@exemple.fr", **autres}

    def test_critere_1_la_reservation_ne_demande_qu_un_nom_et_une_adresse_email(self):
        page = self.client.get(self.url)

        champs = [c for c in page.context["form"].fields if not c.startswith("tarif_")]
        self.assertEqual(champs, ["nom", "email"])
        self.assertNotContains(page, 'type="password"')
        self.assertEqual(self.client.post(self.url, self.donnees()).status_code, 302)  # vers le paiement

    def test_critere_2_une_adresse_mal_ecrite_est_signalee_avant_le_paiement(self):
        reponse = self.client.post(self.url, self.donnees(email="ada@exemple"))

        self.assertEqual(reponse.status_code, 200)  # on reste sur la page : pas de paiement
        self.assertTrue(reponse.context["form"].errors["email"])

    def test_critere_3_un_recapitulatif_s_affiche_avant_le_paiement(self):
        page = self.client.get(self.url)

        for attendu in ("Film test", self.seance.salle.nom, "A1", "A2", "Plein", "20,00 €"):
            self.assertContains(page, attendu)
