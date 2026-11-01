"""E1-US2 : en tant que touriste, je veux utiliser le site en anglais, afin de comprendre l'offre.
Un test par critère d'acceptation de la carte Trello."""
from django.conf import settings
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from billetterie.services import creer_billets, finaliser_billets
from catalogue.models import Tarif
from outils_de_test.fabriques import creer_seance
from paiement.models import Paiement
from paiement.services import confirmer_paiement
from reservation.models import Reservation


class SiteEnAnglaisTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        self.sieges = [str(s.id) for s in self.seance.salle.sieges.all()[:2]]

    def tearDown(self):
        translation.activate(settings.LANGUAGE_CODE)

    def reserver_en_anglais(self):
        return self.client.post(f"/en/reservation/seance/{self.seance.id}/bloquer/", {"sieges": self.sieges}, follow=True)

    def test_critere_1_les_pages_du_parcours_de_reservation_existent_en_anglais(self):
        self.assertContains(self.client.get(f"/en/reservation/seance/{self.seance.id}/"), "Choose your seats")
        self.assertContains(self.reserver_en_anglais(), "Tickets and details")

    def test_critere_2_le_bouton_fr_en_mene_a_la_meme_page_dans_l_autre_langue(self):
        plan = self.client.get(f"/en/reservation/seance/{self.seance.id}/")
        self.assertContains(plan, f'href="/reservation/seance/{self.seance.id}/"')

        recap = self.reserver_en_anglais()
        reference = Reservation.objects.get().reference
        self.assertContains(recap, f'href="/reservation/{reference}/"')

    def test_critere_3_la_langue_choisie_est_gardee_pendant_toute_la_visite(self):
        reponse = self.reserver_en_anglais()

        self.assertTrue(reponse.redirect_chain[-1][0].startswith("/en/reservation/"))
        self.assertContains(reponse, '<html lang="en">')

    def test_le_billet_est_envoye_dans_la_langue_du_spectateur(self):
        self.reserver_en_anglais()
        reservation = Reservation.objects.get()
        reservation.email = "tourist@example.com"
        reservation.save(update_fields=["email"])
        self.assertEqual(reservation.langue, "en")
        creer_billets(reservation, {place.id: Tarif.objects.first() for place in reservation.places.all()})

        translation.activate("fr")  # confirmation reçue de Stripe, sans langue particulière
        with self.captureOnCommitCallbacks(execute=False):
            confirmer_paiement(reservation.id, Paiement.Mode.CARTE_EN_LIGNE)
        finaliser_billets(reservation.id)

        self.assertIn("Your tickets", mail.outbox[0].subject)
        self.assertIn(reverse("billetterie:billet", args=[reservation.reference, reservation.jeton]).replace("/billet", "/en/billet"),
                      mail.outbox[0].body)
