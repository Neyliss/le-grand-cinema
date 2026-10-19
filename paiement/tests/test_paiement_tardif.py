"""RG-06 : un paiement arrivé après la libération des sièges est remboursé automatiquement."""
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from outils_de_test.fabriques import creer_seance, reserver_avec_billets
from paiement.models import Paiement
from paiement.services import PaiementTropTardif, confirmer_paiement
from reservation.models import PlaceSeance
from reservation.services import liberer_places_expirees


class PaiementTardifTests(TestCase):
    def test_paiement_trop_tardif_rembourse(self):
        reservation = reserver_avec_billets(creer_seance(), nb=2)
        reservation.places.update(fin_blocage=timezone.now() - timedelta(seconds=1))
        liberer_places_expirees()  # les 10 minutes sont passées : sièges rendus au stock

        with mock.patch("paiement.services.rembourser_reference") as rembourser:
            with self.assertRaises(PaiementTropTardif):
                confirmer_paiement(reservation.id, Paiement.Mode.CARTE_EN_LIGNE, "cs_test_2")

        rembourser.assert_called_once_with("cs_test_2")
        self.assertFalse(PlaceSeance.objects.filter(statut=PlaceSeance.Statut.VENDUE).exists())
