"""Achat d'une carte d'abonnement avec Stripe : la carte n'est active qu'une fois le paiement
confirmé par Stripe (retour du spectateur ou message signé), et une seule fois."""
import json
from decimal import Decimal
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from fidelite.models import Abonnement, FormuleAbonnement, Offre
from outils_de_test.fabriques import creer_administrateur, creer_spectateur
from paiement.tests.test_webhook import SECRET_WEBHOOK, entete_signature


@override_settings(STRIPE_SECRET_KEY="sk_test_factice", STRIPE_WEBHOOK_SECRET=SECRET_WEBHOOK, PAIEMENT_DEMO=False)
class AchatCarteStripeTests(TestCase):
    def setUp(self):
        self.spectateur = creer_spectateur()
        self.formule = FormuleAbonnement.objects.create(libelle="Carte 10 places", nb_places=10, prix=Decimal("75.00"))
        self.client.force_login(self.spectateur)

    def commander(self):
        with mock.patch("stripe.checkout.Session.create") as creer:
            creer.return_value = mock.Mock(url="https://checkout.stripe.com/c/pay/cs_test_carte")
            reponse = self.client.post(reverse("fidelite:abonnement"), {"formule": self.formule.id})
        return reponse, creer.call_args.kwargs

    def test_la_page_de_paiement_stripe_porte_le_bon_montant_et_la_reference_de_la_carte(self):
        reponse, options = self.commander()

        carte = Abonnement.objects.get()
        self.assertEqual(reponse.url, "https://checkout.stripe.com/c/pay/cs_test_carte")
        self.assertEqual(options["line_items"][0]["price_data"]["unit_amount"], 7500)
        self.assertEqual(options["metadata"], {"abonnement": carte.reference})
        self.assertEqual(carte.statut, Abonnement.Statut.ATTENTE)  # pas encore payée

    def test_retour_de_stripe_la_carte_est_activee_apres_verification(self):
        self.commander()
        carte = Abonnement.objects.get()
        session = {"id": "cs_test_carte", "payment_status": "paid", "metadata": {"abonnement": carte.reference}}

        with mock.patch("stripe.checkout.Session.retrieve", return_value=session):
            self.client.get(reverse("fidelite:retour", args=[carte.reference]), {"session_id": "cs_test_carte"})

        carte.refresh_from_db()
        self.assertEqual((carte.statut, carte.places_restantes), (Abonnement.Statut.ACTIVE, 10))

    def test_message_signe_de_stripe_active_la_carte_une_seule_fois(self):
        self.commander()
        carte = Abonnement.objects.get()
        corps = json.dumps({"id": "evt_1", "object": "event", "type": "checkout.session.completed",
                            "data": {"object": {"id": "cs_test_carte", "object": "checkout.session", "payment_status": "paid",
                                                "metadata": {"abonnement": carte.reference}}}})

        for _ in range(2):  # Stripe peut envoyer deux fois le même message
            self.client.post(reverse("webhook_stripe"), corps, content_type="application/json",
                             HTTP_STRIPE_SIGNATURE=entete_signature(corps))

        carte.refresh_from_db()
        self.assertEqual((carte.statut, carte.places_restantes, carte.reference_stripe), (Abonnement.Statut.ACTIVE, 10, "cs_test_carte"))

    def test_une_carte_ne_se_voit_que_par_son_proprietaire(self):
        self.commander()
        carte = Abonnement.objects.get()
        self.client.force_login(creer_spectateur("bob@exemple.fr"))

        self.assertEqual(self.client.get(reverse("fidelite:retour", args=[carte.reference])).status_code, 404)


class EnvoiOffreAdministrationTests(TestCase):
    def test_la_direction_envoie_l_offre_depuis_l_administration_une_seule_fois(self):
        accepte = creer_spectateur("oui@exemple.fr")
        accepte.profil.accepte_offres = True
        accepte.profil.save()
        offre = Offre.objects.create(titre="Mardi à 6 €", message="Toutes les séances du mardi à 6 €.")
        self.client.force_login(creer_administrateur())
        action = {"action": "envoyer", "_selected_action": [offre.id]}

        self.client.post(reverse("admin:fidelite_offre_changelist"), action)
        self.client.post(reverse("admin:fidelite_offre_changelist"), action)

        offre.refresh_from_db()
        self.assertEqual((len(mail.outbox), offre.nb_destinataires), (1, 1))
