"""E9-US1 : en tant que spectateur régulier, je veux un compte facultatif, afin de retrouver
toutes mes réservations. Un test par critère d'acceptation de la carte Trello."""
import re

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from comptes.services import reservations_du_compte
from outils_de_test.fabriques import acheter_en_ligne, creer_seance, creer_spectateur
from reservation.models import Reservation

MOT_DE_PASSE = "Cinema-2026!"


class CompteSpectateurTests(TestCase):
    def setUp(self):
        self.seance = creer_seance()

    def creer_compte_par_le_site(self, email="ada@exemple.fr"):
        with self.captureOnCommitCallbacks(execute=True):  # l'e-mail part à la fin de l'enregistrement
            return self.client.post(reverse("comptes:inscription"), {
                "nom": "Ada", "email": email, "mot_de_passe": MOT_DE_PASSE, "confirmation": MOT_DE_PASSE})

    def lien_recu_par_email(self):
        return re.search(r"https?://\S+/compte/confirmer/\S+/", mail.outbox[-1].body).group(0)

    def se_connecter(self, email="ada@exemple.fr"):
        return self.client.post(reverse("comptes:connexion"), {"email": email, "mot_de_passe": MOT_DE_PASSE})

    def test_critere_1_je_cree_un_compte_avec_email_et_mot_de_passe_puis_je_confirme_mon_adresse(self):
        self.assertEqual(self.creer_compte_par_le_site().status_code, 200)
        self.assertEqual(mail.outbox[-1].to, ["ada@exemple.fr"])
        # Tant que l'adresse n'est pas confirmée, on ne peut pas se connecter
        self.assertEqual(self.se_connecter().status_code, 200)
        self.assertFalse(User.objects.get(email="ada@exemple.fr").profil.email_confirme)

        lien = self.lien_recu_par_email()
        self.client.get(lien[lien.index("/compte/"):])

        self.assertTrue(User.objects.get(email="ada@exemple.fr").profil.email_confirme)
        self.client.logout()
        self.assertRedirects(self.se_connecter(), reverse("comptes:mon_compte"))
        # Le mot de passe est enregistré chiffré, jamais en clair
        self.assertNotIn(MOT_DE_PASSE, User.objects.get(email="ada@exemple.fr").password)

    def test_critere_2_mes_reservations_passees_avec_la_meme_adresse_sont_rattachees_au_compte(self):
        ancienne = acheter_en_ligne(self.seance, "Ada@Exemple.fr")  # même adresse, majuscules différentes
        autre = acheter_en_ligne(self.seance, "bob@exemple.fr")

        self.creer_compte_par_le_site()
        lien = self.lien_recu_par_email()
        self.client.get(lien[lien.index("/compte/"):])

        spectateur = User.objects.get(email="ada@exemple.fr")
        self.assertEqual(list(reservations_du_compte(spectateur)), [ancienne])
        autre.refresh_from_db()
        self.assertIsNone(autre.compte)
        self.assertContains(self.client.get(reverse("comptes:mon_compte")), f"/billet/{ancienne.reference}/")

    def test_critere_3_je_peux_supprimer_mon_compte_et_mes_donnees_et_reserver_sans_compte_reste_possible(self):
        reservation = acheter_en_ligne(self.seance, "ada@exemple.fr")
        creer_spectateur()
        self.se_connecter()  # la réservation rejoint le compte à la connexion
        self.assertIsNotNone(Reservation.objects.get(pk=reservation.pk).compte)

        self.client.post(reverse("comptes:supprimer"))

        self.assertFalse(User.objects.filter(email="ada@exemple.fr").exists())
        reservation.refresh_from_db()
        self.assertEqual((reservation.nom, reservation.email, reservation.compte), ("", "", None))
        self.assertTrue(reservation.est_payee)  # le billet acheté reste valable
        # Réserver sans compte reste possible : aucune connexion demandée
        self.client.logout()
        sieges = [s.id for s in self.seance.salle.sieges.all()[5:7]]
        reponse = self.client.post(reverse("reservation:bloquer", args=[self.seance.id]), {"sieges": sieges})
        self.assertEqual(reponse.status_code, 302)
        self.assertNotContains(self.client.get(reponse.url), 'type="password"')

    def test_une_reservation_faite_connecte_rejoint_le_compte_avec_nom_et_email_remplis(self):
        spectateur = creer_spectateur()
        self.client.force_login(spectateur)
        sieges = [s.id for s in self.seance.salle.sieges.all()[:1]]

        self.client.post(reverse("reservation:bloquer", args=[self.seance.id]), {"sieges": sieges})

        reservation = Reservation.objects.get()
        self.assertEqual((reservation.compte, reservation.email, reservation.nom), (spectateur, "ada@exemple.fr", "Ada"))

    def test_un_lien_de_confirmation_modifie_est_refuse(self):
        self.creer_compte_par_le_site()
        lien = self.lien_recu_par_email()
        faux = lien[lien.index("/compte/"):-2] + "x/"

        self.assertRedirects(self.client.get(faux), reverse("comptes:inscription"))
        self.assertFalse(User.objects.get(email="ada@exemple.fr").profil.email_confirme)

    def test_on_ne_peut_pas_creer_deux_comptes_avec_la_meme_adresse(self):
        creer_spectateur()

        reponse = self.creer_compte_par_le_site("ADA@exemple.fr")

        self.assertTrue(reponse.context["form"].errors["email"])
        self.assertEqual(User.objects.filter(email="ada@exemple.fr").count(), 1)
