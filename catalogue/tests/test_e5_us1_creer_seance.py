"""E5-US1 : en tant qu'administrateur, je veux créer une séance (film, salle, horaire, tarifs),
afin de la mettre en vente. Un test par critère d'acceptation de la carte Trello."""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalogue.models import Film, Seance, Tarif
from outils_de_test.fabriques import creer_administrateur, creer_seance
from reservation.models import PlaceSeance


class CreerSeanceTests(TestCase):
    def setUp(self):
        self.seance = creer_seance(dans=timedelta(days=1))
        self.jour = timezone.localdate(self.seance.debut)

    def test_critere_1_la_seance_apparait_sur_le_site_des_sa_publication(self):
        reponse = self.client.get(reverse("catalogue:programmation"), {"jour": self.jour.isoformat()})

        self.assertContains(reponse, "Film test")
        self.assertContains(reponse, timezone.localtime(self.seance.debut).strftime("%H:%M"))

    def test_critere_2_chaque_siege_de_la_salle_devient_une_place_libre(self):
        places = self.seance.places.all()

        self.assertEqual(places.count(), self.seance.salle.sieges.count())
        self.assertFalse(places.exclude(statut=PlaceSeance.Statut.LIBRE).exists())

    def test_critere_3_un_tarif_cree_dans_l_administration_est_propose_sans_developpement(self):
        self.client.force_login(creer_administrateur())

        self.client.post(reverse("admin:catalogue_tarif_add"),
                         {"libelle": "Festival", "prix": "7.50", "actif": "on", "ordre": "4"})

        self.assertTrue(Tarif.objects.filter(libelle="Festival", prix=Decimal("7.50")).exists())
        self.assertContains(self.client.get(reverse("catalogue:infos")), "Festival")

    def test_une_salle_ne_peut_pas_accueillir_deux_seances_en_meme_temps(self):
        film = Film.objects.create(titre="Autre film", duree=90)
        chevauchement = Seance(film=film, salle=self.seance.salle, debut=self.seance.debut + timedelta(minutes=30))

        with self.assertRaises(ValidationError):
            chevauchement.full_clean()

    def test_une_seance_apres_la_precedente_est_acceptee(self):
        film = Film.objects.create(titre="Autre film", duree=90)
        suivante = Seance(film=film, salle=self.seance.salle, debut=self.seance.fin + timedelta(minutes=15))

        suivante.full_clean()  # aucune erreur
