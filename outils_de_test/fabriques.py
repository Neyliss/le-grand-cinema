"""
Fabriques de données de test : de petites fonctions qui créent en une ligne
une séance, une vente ou un compte du personnel.

Chaque test part d'une base vide (Django la remet à zéro entre deux tests) :
il crée lui-même les données dont il a besoin, avec ces fabriques.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.utils import timezone

from billetterie.services import creer_billets
from catalogue.models import Film, Salle, Seance, Tarif
from grandcinema.acces import GROUPE_ADMINISTRATEURS, GROUPE_AGENTS
from paiement.models import Paiement
from paiement.services import confirmer_paiement
from reservation.models import Reservation
from reservation.services import creer_reservation


def creer_seance(rangees=3, par_rangee=5, dans=timedelta(days=1)):
    """Petite salle de test : 3 rangées de 5 sièges (15 places, dont 2 PMR), tarif Plein à 10 €."""
    salle = Salle.objects.create(nom=f"Salle test {Salle.objects.count() + 1}", allees="2")
    salle.generer_sieges(rangees, par_rangee)
    film = Film.objects.create(titre="Film test", duree=100)
    Tarif.objects.get_or_create(libelle="Plein", prix=Decimal("10.00"))
    return Seance.objects.create(film=film, salle=salle, debut=timezone.now() + dans)


def reserver_avec_billets(seance, nb=1, canal=Reservation.Canal.SITE):
    """Réservation en attente de paiement : les `nb` premiers sièges libres sont bloqués et les billets préparés."""
    libres = seance.places.filter(statut="libre").order_by("siege__rangee", "siege__numero")
    reservation = creer_reservation(seance, list(libres.values_list("siege_id", flat=True)[:nb]), canal=canal)
    tarif = Tarif.objects.first()
    creer_billets(reservation, {place.id: tarif for place in reservation.places.all()})
    return reservation


def vendre(seance, nb=1):
    """Vente payée de `nb` places au guichet, par carte."""
    reservation = reserver_avec_billets(seance, nb, canal=Reservation.Canal.GUICHET)
    confirmer_paiement(reservation.id, Paiement.Mode.GUICHET_CARTE)
    return reservation


def acheter_en_ligne(seance, email, nb=1):
    """Achat payé sur le site, par carte, avec cette adresse e-mail (sans compte)."""
    reservation = reserver_avec_billets(seance, nb)
    reservation.nom, reservation.email = "Ada", email
    reservation.save(update_fields=["nom", "email"])
    return confirmer_paiement(reservation.id, Paiement.Mode.CARTE_EN_LIGNE)


def creer_spectateur(email="ada@exemple.fr", mot_de_passe="Cinema-2026!", confirme=True):
    """Compte spectateur (E9-US1), adresse déjà confirmée par défaut."""
    from comptes.services import creer_compte

    spectateur = creer_compte(email, mot_de_passe, "Ada")
    spectateur.profil.email_confirme = confirme
    spectateur.profil.save()
    return spectateur


def creer_abonne(email="ada@exemple.fr", places=10):
    """Spectateur confirmé avec une carte d'abonnement active, et le tarif « Abonné » (0 €) créé."""
    from fidelite.models import Abonnement, FormuleAbonnement

    spectateur = creer_spectateur(email)
    formule, _ = FormuleAbonnement.objects.get_or_create(libelle="Carte 10 places", nb_places=10, prix=Decimal("75.00"))
    Abonnement.objects.create(compte=spectateur, formule=formule, prix=formule.prix, places_restantes=places,
                              statut=Abonnement.Statut.ACTIVE, active_le=timezone.now())
    Tarif.objects.get_or_create(libelle="Abonné", prix=Decimal("0.00"), reserve_abonnes=True)
    return spectateur


def creer_agent(identifiant="agent"):
    """Compte d'agent d'accueil : membre du personnel, groupe « Agents d'accueil »."""
    agent = User.objects.create_user(identifiant, password="mot-de-passe-de-test", is_staff=True)
    agent.groups.add(Group.objects.get_or_create(name=GROUPE_AGENTS)[0])
    return agent


def creer_administrateur(identifiant="direction"):
    """Compte d'administrateur : groupe « Administrateurs », avec les mêmes droits que sur le site
    (programmation, réservations, paiements, billets)."""
    admin = User.objects.create_user(identifiant, password="mot-de-passe-de-test", is_staff=True)
    groupe = Group.objects.get_or_create(name=GROUPE_ADMINISTRATEURS)[0]
    groupe.permissions.set(Permission.objects.filter(
        content_type__app_label__in=["catalogue", "reservation", "paiement", "billetterie"]))
    admin.groups.add(groupe)
    return admin
