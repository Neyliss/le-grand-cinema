"""
Fabriques de données de test : de petites fonctions qui créent en une ligne
une séance, une vente ou un compte du personnel.

Chaque test part d'une base vide (Django la remet à zéro entre deux tests) :
il crée lui-même les données dont il a besoin, avec ces fabriques.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.utils import timezone

from billetterie.services import creer_billets
from catalogue.models import Film, Salle, Seance, Tarif
from grandcinema.acces import GROUPE_ADMINISTRATEURS, GROUPE_AGENTS
from paiement.models import Paiement
from paiement.services import confirmer_paiement
from reservation.services import creer_reservation


def creer_seance(rangees=3, par_rangee=5, dans=timedelta(days=1)):
    """Petite salle de test : 3 rangées de 5 sièges (15 places, dont 2 PMR), tarif Plein à 10 €."""
    salle = Salle.objects.create(nom=f"Salle test {Salle.objects.count() + 1}", allees="2")
    salle.generer_sieges(rangees, par_rangee)
    film = Film.objects.create(titre="Film test", duree=100)
    Tarif.objects.get_or_create(libelle="Plein", prix=Decimal("10.00"))
    return Seance.objects.create(film=film, salle=salle, debut=timezone.now() + dans)


def reserver_avec_billets(seance, nb=1):
    """Réservation en attente de paiement : sièges bloqués et billets préparés."""
    reservation = creer_reservation(seance, [s.id for s in seance.salle.sieges.all()[:nb]])
    tarif = Tarif.objects.first()
    creer_billets(reservation, {place.id: tarif for place in reservation.places.all()})
    return reservation


def vendre(seance, nb=1):
    """Vente payée de `nb` places (comme au guichet, par carte)."""
    reservation = reserver_avec_billets(seance, nb)
    confirmer_paiement(reservation.id, Paiement.Mode.GUICHET_CARTE)
    return reservation


def creer_agent(identifiant="agent"):
    """Compte d'agent d'accueil : membre du personnel, groupe « Agents d'accueil »."""
    agent = User.objects.create_user(identifiant, password="mot-de-passe-de-test", is_staff=True)
    agent.groups.add(Group.objects.get_or_create(name=GROUPE_AGENTS)[0])
    return agent


def creer_administrateur(identifiant="direction"):
    """Compte d'administrateur : groupe « Administrateurs »."""
    admin = User.objects.create_user(identifiant, password="mot-de-passe-de-test", is_staff=True)
    admin.groups.add(Group.objects.get_or_create(name=GROUPE_ADMINISTRATEURS)[0])
    return admin
