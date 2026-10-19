"""
Règle critique (dossier 3, § 3.3, RG-01) : un siège ne se vend qu'une fois.

Chaque test suit le schéma « Préparer / Agir / Vérifier » (voir docs/guide-tests.md).
"""
import threading

from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from outils_de_test.fabriques import creer_seance
from reservation.models import PlaceSeance, Reservation
from reservation.services import SiegeIndisponible, bloquer_sieges, creer_reservation


class DoubleVenteTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        self.sieges = list(self.seance.salle.sieges.all()[:2])

    def test_un_siege_bloque_ne_peut_pas_etre_bloque_une_seconde_fois(self):
        # Préparer : un premier spectateur bloque deux sièges
        creer_reservation(self.seance, [s.id for s in self.sieges])

        # Agir et vérifier : un second spectateur demande l'un de ces sièges
        with self.assertRaises(SiegeIndisponible):
            creer_reservation(self.seance, [self.sieges[1].id])

    def test_tout_ou_rien_si_un_seul_siege_est_pris(self):
        creer_reservation(self.seance, [self.sieges[0].id])
        autre = self.seance.salle.sieges.all()[4]

        with self.assertRaises(SiegeIndisponible):
            creer_reservation(self.seance, [autre.id, self.sieges[0].id])

        # Le siège encore libre n'a pas été bloqué : la transaction a tout annulé
        self.assertEqual(self.seance.places.get(siege=autre).statut, PlaceSeance.Statut.LIBRE)

    def test_contrainte_unique_seance_siege_dans_la_base(self):
        # Même en contournant le code, la base refuse une seconde place pour le même siège
        with self.assertRaises(IntegrityError), transaction.atomic():
            PlaceSeance.objects.create(seance=self.seance, siege=self.sieges[0])

    def test_un_siege_vendu_reste_indisponible(self):
        reservation = creer_reservation(self.seance, [self.sieges[0].id])
        reservation.places.update(statut=PlaceSeance.Statut.VENDUE)

        with self.assertRaises(SiegeIndisponible):
            bloquer_sieges(self.seance, [self.sieges[0]], Reservation.objects.create(seance=self.seance))


@skipUnlessDBFeature("has_select_for_update")
class ConcurrenceReelleTests(TransactionTestCase):
    """Cinq spectateurs cliquent en même temps sur le même siège (vraies connexions parallèles).
    Ce test tourne avec PostgreSQL (verrous de lignes) ; SQLite n'a pas ces verrous, il est ignoré."""

    def test_un_seul_spectateur_obtient_le_siege(self):
        # Préparer : un siège libre et cinq spectateurs prêts à partir ensemble
        seance = creer_seance()
        siege_id = seance.salle.sieges.first().id
        depart = threading.Barrier(5)
        resultats = []

        def spectateur():
            try:
                depart.wait()                          # tous partent au même instant
                creer_reservation(seance, [siege_id])
                resultats.append("obtenu")
            except SiegeIndisponible:
                resultats.append("refusé")
            finally:
                connection.close()                     # chaque fil a sa propre connexion

        # Agir
        fils = [threading.Thread(target=spectateur) for _ in range(5)]
        for f in fils:
            f.start()
        for f in fils:
            f.join()

        # Vérifier : un seul spectateur a obtenu le siège
        self.assertEqual(sorted(resultats), ["obtenu"] + ["refusé"] * 4)
        self.assertEqual(seance.places.get(siege_id=siege_id).statut, PlaceSeance.Statut.BLOQUEE)
