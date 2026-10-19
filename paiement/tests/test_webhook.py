"""
Webhook Stripe : seul un message signé avec le secret du cinéma confirme un paiement,
et un même message reçu deux fois n'a aucun effet.
"""
import hashlib
import hmac
import json
import tempfile
import time

from django.test import TestCase, override_settings
from django.urls import reverse

from outils_de_test.fabriques import creer_seance, reserver_avec_billets
from paiement.models import Paiement
from reservation.models import Reservation

SECRET_WEBHOOK = "whsec_test"


def entete_signature(corps):
    """Calcule l'en-tête Stripe-Signature comme le fait Stripe."""
    horodatage = int(time.time())
    signature = hmac.new(SECRET_WEBHOOK.encode(), f"{horodatage}.{corps}".encode(), hashlib.sha256).hexdigest()
    return f"t={horodatage},v1={signature}"


@override_settings(STRIPE_SECRET_KEY="sk_test_factice", STRIPE_WEBHOOK_SECRET=SECRET_WEBHOOK, MEDIA_ROOT=tempfile.mkdtemp())
class WebhookTests(TestCase):
    def setUp(self):
        self.reservation = reserver_avec_billets(creer_seance(), nb=2)

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
        # Le refus est écrit dans le journal : on vérifie qu'il l'est, au lieu de l'afficher
        with self.assertLogs("paiement.views", "WARNING") as journal, self.assertLogs("django.request", "WARNING"):
            reponse = self.envoyer_webhook(signature="t=1,v1=fausse")

        self.assertEqual(reponse.status_code, 400)
        self.assertIn("signature invalide", journal.output[0])
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.Statut.ATTENTE)

    def test_webhook_recu_deux_fois_sans_effet(self):
        self.envoyer_webhook()
        self.envoyer_webhook()

        self.assertEqual(Paiement.objects.count(), 1)
