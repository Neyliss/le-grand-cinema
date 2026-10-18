"""E3-US2 : la session Stripe Checkout contient une ligne par billet, avec le prix en centimes."""
from unittest import mock

from django.test import RequestFactory, TestCase, override_settings

from outils_de_test.fabriques import creer_seance, reserver_avec_billets
from paiement.services import url_de_paiement


@override_settings(STRIPE_SECRET_KEY="sk_test_factice")
class CheckoutTests(TestCase):
    def test_session_checkout_creee_avec_les_billets(self):
        reservation = reserver_avec_billets(creer_seance(), nb=2)
        reponse_stripe = mock.Mock(url="https://checkout.stripe.com/c/pay/x")

        # Stripe est remplacé par un « double » (mock) qui enregistre les paramètres reçus
        with mock.patch("stripe.checkout.Session.create", return_value=reponse_stripe) as creer:
            url = url_de_paiement(RequestFactory().get("/"), reservation)

        self.assertEqual(url, "https://checkout.stripe.com/c/pay/x")
        parametres = creer.call_args.kwargs
        self.assertEqual(len(parametres["line_items"]), 2)
        self.assertEqual(parametres["line_items"][0]["price_data"]["unit_amount"], 1000)  # 10 € en centimes
        self.assertEqual(parametres["metadata"]["reservation"], reservation.reference)
