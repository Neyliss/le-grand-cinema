"""Paiement Stripe (E3-US2) : session Checkout, webhook signé, paiement trop tardif.
Les appels à Stripe sont simulés : les tests ne demandent ni clé ni accès à Internet."""
import hashlib
import hmac
import json
import tempfile
import time
from datetime import timedelta
from unittest import mock

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from billetterie.services import creer_billets
from catalogue.models import Tarif
from reservation.models import PlaceSeance, Reservation
from reservation.services import creer_reservation, liberer_places_expirees
from reservation.tests import creer_seance

from .models import Paiement
from .services import PaiementTropTardif, confirmer_paiement, url_de_paiement

SECRET_WEBHOOK = "whsec_test"


def reservation_prete(seance):
    reservation = creer_reservation(seance, [s.id for s in seance.salle.sieges.all()[:2]])
    creer_billets(reservation, {p.id: Tarif.objects.first() for p in reservation.places.all()})
    return reservation


def entete_signature(corps):
    """Calcule l'en-tête Stripe-Signature comme le fait Stripe."""
    horodatage = int(time.time())
    signature = hmac.new(SECRET_WEBHOOK.encode(), f"{horodatage}.{corps}".encode(), hashlib.sha256).hexdigest()
    return f"t={horodatage},v1={signature}"


@override_settings(STRIPE_SECRET_KEY="sk_test_factice", STRIPE_WEBHOOK_SECRET=SECRET_WEBHOOK, MEDIA_ROOT=tempfile.mkdtemp())
class StripeTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        self.reservation = reservation_prete(self.seance)

    def test_session_checkout_creee_avec_les_billets(self):
        requete = RequestFactory().get("/")
        with mock.patch("stripe.checkout.Session.create", return_value=mock.Mock(url="https://checkout.stripe.com/c/pay/x")) as creer:
            url = url_de_paiement(requete, self.reservation)
        self.assertEqual(url, "https://checkout.stripe.com/c/pay/x")
        parametres = creer.call_args.kwargs
        self.assertEqual(len(parametres["line_items"]), 2)
        self.assertEqual(parametres["line_items"][0]["price_data"]["unit_amount"], 1000)  # en centimes
        self.assertEqual(parametres["metadata"]["reservation"], self.reservation.reference)

    def envoyer_webhook(self, signature=None):
        corps = json.dumps({
            "id": "evt_1", "object": "event", "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test_1", "object": "checkout.session", "payment_status": "paid",
                                "metadata": {"reservation": self.reservation.reference}}},
        })
        return self.client.post(reverse("webhook_stripe"), corps, content_type="application/json",
                                HTTP_STRIPE_SIGNATURE=signature or entete_signature(corps))

    def test_webhook_signe_confirme_le_paiement(self):
        with self.captureOnCommitCallbacks(execute=True):
            reponse = self.envoyer_webhook()
        self.assertEqual(reponse.status_code, 200)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.Statut.PAYEE)
        self.assertEqual(self.reservation.paiement.reference_stripe, "cs_test_1")

    def test_webhook_avec_fausse_signature_refuse(self):
        reponse = self.envoyer_webhook(signature="t=1,v1=fausse")
        self.assertEqual(reponse.status_code, 400)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.Statut.ATTENTE)

    def test_webhook_recu_deux_fois_sans_effet(self):
        self.envoyer_webhook()
        self.envoyer_webhook()
        self.assertEqual(Paiement.objects.count(), 1)

    def test_paiement_trop_tardif_rembourse(self):
        self.reservation.places.update(fin_blocage=timezone.now() - timedelta(seconds=1))
        liberer_places_expirees()
        with mock.patch("paiement.services.rembourser_reference") as rembourser:
            with self.assertRaises(PaiementTropTardif):
                confirmer_paiement(self.reservation.id, Paiement.Mode.CARTE_EN_LIGNE, "cs_test_2")
        rembourser.assert_called_once_with("cs_test_2")
        self.assertFalse(PlaceSeance.objects.filter(statut=PlaceSeance.Statut.VENDUE).exists())
