"""E3-US2 : en tant que spectateur, je veux payer par carte en ligne, afin de ne pas passer au guichet.
Un test par critère d'acceptation de la carte Trello."""
from datetime import timedelta
from unittest import mock

from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from outils_de_test.fabriques import creer_seance, reserver_avec_billets
from paiement.models import Paiement
from paiement.services import PaiementTropTardif, confirmer_session_stripe, url_de_paiement
from reservation.models import PlaceSeance, Reservation
from reservation.services import liberer_places_expirees


def session_payee(reservation, identifiant="cs_test_1"):
    return {"id": identifiant, "payment_status": "paid", "metadata": {"reservation": reservation.reference}}


@override_settings(STRIPE_SECRET_KEY="sk_test_factice")
class PayerParCarteTests(TestCase):
    def setUp(self):
        self.reservation = reserver_avec_billets(creer_seance(), nb=2)

    def test_critere_1_le_paiement_se_fait_chez_stripe_sans_donnee_de_carte_au_cinema(self):
        with mock.patch("stripe.checkout.Session.create", return_value=mock.Mock(url="https://checkout.stripe.com/x")):
            url = url_de_paiement(RequestFactory().get("/"), self.reservation)

        self.assertTrue(url.startswith("https://checkout.stripe.com/"))
        champs = {f.name for f in Paiement._meta.get_fields()}
        self.assertFalse(champs & {"numero_carte", "carte", "cvc", "cvv", "expiration"})

    def test_critere_2_la_reservation_passe_a_payee_seulement_quand_stripe_confirme(self):
        self.assertEqual(self.reservation.statut, Reservation.Statut.ATTENTE)
        self.assertEqual(confirmer_session_stripe({"payment_status": "unpaid", "metadata": {}}), None)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.Statut.ATTENTE)

        with self.captureOnCommitCallbacks(execute=False):
            confirmer_session_stripe(session_payee(self.reservation))
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.Statut.PAYEE)

    def test_critere_3_un_paiement_arrive_apres_les_10_minutes_est_rembourse(self):
        self.reservation.places.update(fin_blocage=timezone.now() - timedelta(seconds=1))
        liberer_places_expirees()

        with mock.patch("paiement.services.rembourser_reference") as rembourser, self.assertRaises(PaiementTropTardif):
            confirmer_session_stripe(session_payee(self.reservation, "cs_test_tardif"))
        rembourser.assert_called_once_with("cs_test_tardif")
        self.assertFalse(PlaceSeance.objects.filter(statut=PlaceSeance.Statut.VENDUE).exists())

    def test_la_page_de_stripe_s_affiche_dans_la_langue_du_spectateur(self):
        self.reservation.langue = "en"
        self.reservation.save(update_fields=["langue"])

        with mock.patch("stripe.checkout.Session.create", return_value=mock.Mock(url="https://checkout.stripe.com/x")) as creer:
            url_de_paiement(RequestFactory().get("/"), self.reservation)

        self.assertEqual(creer.call_args.kwargs["locale"], "en")
