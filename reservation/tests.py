"""
Tests de la règle critique (dossier 3, § 3.3) : un siège ne se vend qu'une fois.
Lancer tous les tests : python manage.py test
"""
import tempfile
import threading
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from catalogue.models import Film, Salle, Seance, Tarif

from .models import PlaceSeance, Reservation
from .services import SiegeIndisponible, bloquer_sieges, creer_reservation, liberer_places_expirees, plan_de_salle


def creer_seance(rangees=3, par_rangee=5, dans=timedelta(days=1)):
    """Petite salle de test : 3 rangées de 5 sièges."""
    salle = Salle.objects.create(nom=f"Salle test {Salle.objects.count() + 1}", allees="2")
    salle.generer_sieges(rangees, par_rangee)
    film = Film.objects.create(titre="Film test", duree=100)
    Tarif.objects.get_or_create(libelle="Plein", prix=Decimal("10.00"))
    return Seance.objects.create(film=film, salle=salle, debut=timezone.now() + dans)


class GenerationDesPlacesTests(TestCase):
    def test_une_place_libre_par_siege_a_la_creation_de_la_seance(self):
        seance = creer_seance()
        self.assertEqual(seance.places.count(), 15)
        self.assertTrue(all(p.statut == PlaceSeance.Statut.LIBRE for p in seance.places.all()))

    def test_sieges_pmr_sur_la_derniere_rangee(self):
        seance = creer_seance()
        pmr = seance.salle.sieges.filter(type="pmr")
        self.assertEqual([str(s) for s in pmr], ["C1", "C2"])


class DoubleVenteTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        self.sieges = list(self.seance.salle.sieges.all()[:2])

    def test_un_siege_bloque_ne_peut_pas_etre_bloque_une_seconde_fois(self):
        creer_reservation(self.seance, [s.id for s in self.sieges])
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

        fils = [threading.Thread(target=spectateur) for _ in range(5)]
        for f in fils:
            f.start()
        for f in fils:
            f.join()
        self.assertEqual(sorted(resultats), ["obtenu"] + ["refusé"] * 4)
        self.assertEqual(seance.places.get(siege_id=siege_id).statut, PlaceSeance.Statut.BLOQUEE)


class BlocageDixMinutesTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()
        self.siege = self.seance.salle.sieges.first()

    def test_les_sieges_sont_bloques_dix_minutes(self):
        reservation = creer_reservation(self.seance, [self.siege.id])
        place = reservation.places.get()
        self.assertEqual(place.statut, PlaceSeance.Statut.BLOQUEE)
        restant = place.fin_blocage - timezone.now()
        self.assertTrue(timedelta(minutes=9) < restant <= timedelta(minutes=10))

    def test_un_blocage_expire_libere_le_siege(self):
        reservation = creer_reservation(self.seance, [self.siege.id])
        reservation.places.update(fin_blocage=timezone.now() - timedelta(seconds=1))
        self.assertEqual(liberer_places_expirees(), 1)
        self.assertEqual(self.seance.places.get(siege=self.siege).statut, PlaceSeance.Statut.LIBRE)
        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, Reservation.Statut.ANNULEE)

    def test_un_autre_spectateur_peut_reprendre_un_siege_expire(self):
        premiere = creer_reservation(self.seance, [self.siege.id])
        premiere.places.update(fin_blocage=timezone.now() - timedelta(seconds=1))
        seconde = creer_reservation(self.seance, [self.siege.id])
        self.assertEqual(seconde.places.get().siege, self.siege)


class PlanDeSalleTests(TestCase):
    def test_le_plan_json_indique_le_statut_de_chaque_siege(self):
        seance = creer_seance()
        siege = seance.salle.sieges.first()
        creer_reservation(seance, [siege.id])
        reponse = self.client.get(reverse("reservation:api_plan", args=[seance.id]))
        self.assertEqual(reponse.status_code, 200)
        donnees = reponse.json()
        statuts = {s["id"]: s["statut"] for r in donnees["rangees"] for s in r["sieges"]}
        self.assertEqual(statuts[siege.id], "bloquee")
        self.assertEqual(donnees["libres"], 14)
        self.assertEqual(donnees["allees"], [2])

    def test_seance_passee_non_reservable(self):
        seance = creer_seance(dans=-timedelta(hours=1))
        self.assertFalse(plan_de_salle(seance)["reservable"])
        reponse = self.client.post(reverse("reservation:bloquer", args=[seance.id]), {"sieges": [seance.salle.sieges.first().id]})
        self.assertRedirects(reponse, reverse("catalogue:programmation"))


@override_settings(PAIEMENT_DEMO=True, STRIPE_SECRET_KEY="", MEDIA_ROOT=tempfile.mkdtemp())
class ParcoursEnLigneTests(TestCase):
    """Parcours complet du spectateur, en mode démonstration (sans clé Stripe)."""

    def test_reservation_paiement_et_billet(self):
        seance = creer_seance()
        sieges = list(seance.salle.sieges.all()[:2])
        reponse = self.client.post(reverse("reservation:bloquer", args=[seance.id]), {"sieges": [s.id for s in sieges]})
        reservation = Reservation.objects.get()
        self.assertRedirects(reponse, reverse("reservation:recapitulatif", args=[reservation.reference]))

        tarif = Tarif.objects.get()
        donnees = {"nom": "Marie Dupont", "email": "marie@exemple.fr"}
        for place in reservation.places.all():
            donnees[f"tarif_{place.id}"] = tarif.id
        reponse = self.client.post(reverse("reservation:recapitulatif", args=[reservation.reference]), donnees)
        self.assertRedirects(reponse, reverse("paiement:demo", args=[reservation.reference]))

        with self.captureOnCommitCallbacks(execute=True):
            reponse = self.client.post(reverse("paiement:demo", args=[reservation.reference]))
        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, Reservation.Statut.PAYEE)
        self.assertRedirects(reponse, reverse("billetterie:billet", args=[reservation.reference, reservation.jeton]))
        self.assertTrue(all(p.statut == PlaceSeance.Statut.VENDUE for p in reservation.places.all()))
        self.assertEqual(reservation.paiement.montant, Decimal("20.00"))

        from django.core import mail

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["marie@exemple.fr"])
        self.assertEqual(mail.outbox[0].attachments[0][2], "application/pdf")

    def test_la_reservation_d_un_autre_navigateur_est_invisible(self):
        seance = creer_seance()
        reservation = creer_reservation(seance, [seance.salle.sieges.first().id])
        reponse = self.client.get(reverse("reservation:recapitulatif", args=[reservation.reference]))
        self.assertEqual(reponse.status_code, 404)
