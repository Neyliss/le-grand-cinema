"""E10-US1 : en tant que spectateur régulier, je veux un abonnement et des offres réservées aux
habitués, afin de payer moins cher et de venir plus souvent. Un test par critère d'acceptation."""
from decimal import Decimal

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from catalogue.models import Tarif
from comptes.services import creer_compte
from fidelite.models import Abonnement, FormuleAbonnement, Offre
from fidelite.services import envoyer_offre
from outils_de_test.fabriques import creer_abonne, creer_administrateur, creer_seance, creer_spectateur
from paiement.models import Paiement
from reservation.models import Reservation
from reservation.services import annuler_seance


class AbonnementTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()

    def reserver(self, nb=2):
        """Le spectateur choisit `nb` sièges libres : on arrive sur le récapitulatif."""
        libres = self.seance.places.filter(statut="libre").order_by("siege__rangee", "siege__numero")
        sieges = list(libres.values_list("siege_id", flat=True)[:nb])
        self.client.post(reverse("reservation:bloquer", args=[self.seance.id]), {"sieges": sieges})
        reservation = Reservation.objects.filter(statut=Reservation.Statut.ATTENTE).latest("cree_le")
        return reservation, reverse("reservation:recapitulatif", args=[reservation.reference])

    def choisir(self, reservation, tarifs):
        donnees = {"nom": "Ada", "email": "ada@exemple.fr"}
        for place, tarif in zip(reservation.places.order_by("siege__numero"), tarifs):
            donnees[f"tarif_{place.id}"] = str(tarif.id)
        return donnees

    def test_critere_1_une_carte_s_achete_en_ligne_et_se_decompte_a_chaque_reservation(self):
        spectateur = creer_spectateur()
        formule = FormuleAbonnement.objects.create(libelle="Carte 10 places", nb_places=10, prix=Decimal("75.00"))
        abonne = Tarif.objects.create(libelle="Abonné", prix=Decimal("0.00"), reserve_abonnes=True)
        self.client.force_login(spectateur)

        # Achat en ligne (paiement simulé du site de démonstration)
        reponse = self.client.post(reverse("fidelite:abonnement"), {"formule": formule.id})
        carte = Abonnement.objects.get(compte=spectateur)
        self.assertRedirects(reponse, reverse("fidelite:demo", args=[carte.reference]))
        self.client.post(reponse.url)
        carte.refresh_from_db()
        self.assertEqual((carte.statut, carte.places_restantes), (Abonnement.Statut.ACTIVE, 10))

        # Réservation de 2 places au tarif « Abonné » : rien à payer, la carte passe à 8
        reservation, url = self.reserver(2)
        self.client.post(url, self.choisir(reservation, [abonne, abonne]))
        reservation.refresh_from_db()
        carte.refresh_from_db()
        self.assertTrue(reservation.est_payee)
        self.assertEqual((reservation.paiement.mode, reservation.abonnement, carte.places_restantes),
                         (Paiement.Mode.ABONNEMENT, carte, 8))

    def test_critere_1_bis_une_place_avec_la_carte_et_une_place_payee_par_carte_bancaire(self):
        self.client.force_login(creer_abonne(places=10))
        plein, abonne = Tarif.objects.get(libelle="Plein"), Tarif.objects.get(libelle="Abonné")
        reservation, url = self.reserver(2)

        reponse = self.client.post(url, self.choisir(reservation, [abonne, plein]))
        self.client.post(reponse.url)  # page de paiement (démonstration) : 10 € à payer

        reservation.refresh_from_db()
        self.assertEqual((reservation.paiement.montant, reservation.abonnement.places_restantes), (Decimal("10.00"), 9))

    def test_critere_2_les_offres_ne_vont_qu_aux_spectateurs_qui_l_ont_accepte(self):
        # La case est décochée par défaut sur la page de création du compte
        page = self.client.get(reverse("comptes:inscription"))
        self.assertFalse(page.context["form"].fields["accepte_offres"].initial)
        self.assertNotContains(page, "checked")
        accepte = creer_spectateur("oui@exemple.fr")
        accepte.profil.accepte_offres = True
        accepte.profil.save()
        creer_spectateur("non@exemple.fr")  # n'a rien coché
        creer_compte("pas-confirme@exemple.fr", "Cinema-2026!", accepte_offres=True)  # adresse non confirmée
        mail.outbox.clear()

        nb = envoyer_offre(Offre.objects.create(titre="Mardi à 6 €", message="Toutes les séances du mardi à 6 €."), "https://exemple.fr")

        self.assertEqual(nb, 1)
        self.assertEqual([m.to for m in mail.outbox], [["oui@exemple.fr"]])  # un e-mail par personne, sans copie
        self.assertIn("décochez la case", mail.outbox[0].body)

    def test_critere_2_bis_le_spectateur_change_son_choix_dans_son_compte(self):
        spectateur = creer_spectateur()
        self.client.force_login(spectateur)

        self.client.post(reverse("comptes:preferences"), {"accepte_offres": "on"})
        spectateur.profil.refresh_from_db()
        self.assertTrue(spectateur.profil.accepte_offres)
        self.client.post(reverse("comptes:preferences"), {})
        spectateur.profil.refresh_from_db()
        self.assertFalse(spectateur.profil.accepte_offres)

    def test_critere_3_le_tarif_abonne_se_cree_dans_l_administration_sans_developpement(self):
        self.client.force_login(creer_administrateur())
        self.client.post(reverse("admin:catalogue_tarif_add"), {
            "libelle": "Abonné", "prix": "0.00", "actif": "on", "reserve_abonnes": "on", "ordre": "9"})
        abonne = Tarif.objects.get(libelle="Abonné")
        self.assertTrue(abonne.reserve_abonnes)
        self.client.logout()

        # Proposé au spectateur qui a une carte…
        self.client.force_login(creer_abonne())
        reservation, url = self.reserver(1)
        self.assertIn(abonne, self.client.get(url).context["form"].fields[f"tarif_{reservation.places.get().id}"].queryset)
        # … mais pas au visiteur sans carte, ni au guichet
        self.client.logout()
        reservation, url = self.reserver(1)
        self.assertNotIn(abonne, self.client.get(url).context["form"].fields[f"tarif_{reservation.places.get().id}"].queryset)
        self.assertNotIn(abonne, Tarif.objects.publics())

    def test_on_ne_peut_pas_prendre_plus_de_places_que_la_carte_n_en_a(self):
        self.client.force_login(creer_abonne(places=1))
        abonne = Tarif.objects.get(libelle="Abonné")
        reservation, url = self.reserver(2)

        reponse = self.client.post(url, self.choisir(reservation, [abonne, abonne]))

        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.context["form"].non_field_errors())
        self.assertEqual(Abonnement.objects.get().places_restantes, 1)

    def test_seance_annulee_les_places_sont_rendues_a_la_carte(self):
        self.client.force_login(creer_abonne(places=10))
        abonne = Tarif.objects.get(libelle="Abonné")
        reservation, url = self.reserver(3)
        self.client.post(url, self.choisir(reservation, [abonne] * 3))
        self.assertEqual(Abonnement.objects.get().places_restantes, 7)

        annuler_seance(self.seance)

        self.assertEqual(Abonnement.objects.get().places_restantes, 10)

    def test_une_nouvelle_carte_ne_s_achete_que_quand_la_precedente_est_epuisee(self):
        self.client.force_login(creer_abonne(places=2))

        self.client.post(reverse("fidelite:abonnement"), {"formule": FormuleAbonnement.objects.get().id})

        self.assertEqual(Abonnement.objects.count(), 1)
