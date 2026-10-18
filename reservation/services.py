"""
Règles métier de la réservation. Elles sont regroupées ici, et non dans les vues,
pour être utilisées à l'identique par le site et par le guichet.

La règle critique (dossier 3, § 3.3) : un siège ne se vend qu'une fois.
Elle repose sur deux niveaux de protection :
  1. un verrou sur les lignes de la base pendant la transaction (select_for_update) ;
  2. la contrainte d'unicité « séance + siège » de la table PlaceSeance.
"""
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import PlaceSeance, Reservation


class SiegeIndisponible(Exception):
    """Au moins un des sièges demandés n'est plus libre."""


class SeanceNonReservable(Exception):
    """La séance est annulée ou déjà commencée."""


def duree_blocage():
    return timedelta(minutes=settings.DUREE_BLOCAGE_MINUTES)


def liberer_places_expirees(seance=None):
    """Remet « libres » les sièges dont le blocage de 10 minutes est dépassé.
    Appelée à chaque lecture du plan et par la tâche planifiée « liberer_places »."""
    from billetterie.models import Billet

    with transaction.atomic():
        places = PlaceSeance.objects.select_for_update().bloquees_expirees()
        if seance is not None:
            places = places.filter(seance=seance)
        expirees = list(places.values_list("id", "reservation_id"))
        if not expirees:
            return 0
        ids = [place_id for place_id, _ in expirees]
        reservations = {reservation_id for _, reservation_id in expirees}
        # Les billets provisoires de ces places sont supprimés…
        Billet.objects.filter(place_id__in=ids).delete()
        PlaceSeance.objects.filter(id__in=ids).update(statut=PlaceSeance.Statut.LIBRE, reservation=None, fin_blocage=None)
        # … et les réservations non payées restées sans place sont annulées.
        Reservation.objects.filter(id__in=reservations, statut=Reservation.Statut.ATTENTE) \
            .exclude(places__isnull=False).update(statut=Reservation.Statut.ANNULEE)
    return len(ids)


@transaction.atomic                                   # tout ou rien
def bloquer_sieges(seance, sieges, reservation):
    """Bloque les sièges choisis pendant 10 minutes (code présenté au § 3.3 du dossier 3)."""
    liberer_places_expirees(seance)
    places = list(PlaceSeance.objects
                  .select_for_update()                # verrou sur ces lignes
                  .filter(seance=seance, siege__in=sieges))
    if len(places) != len(sieges) or any(p.statut != "libre" for p in places):
        raise SiegeIndisponible()                     # déjà pris : on annule tout
    fin = timezone.now() + duree_blocage()
    for p in places:
        p.statut, p.reservation, p.fin_blocage = "bloquee", reservation, fin
        p.save()
    return places


@transaction.atomic
def creer_reservation(seance, siege_ids, canal=Reservation.Canal.SITE):
    """Crée une réservation « en attente » et bloque ses sièges. Lève SiegeIndisponible si un siège est pris."""
    if not seance.est_reservable:
        raise SeanceNonReservable()
    if not siege_ids or len(siege_ids) > settings.PLACES_MAX_PAR_RESERVATION:
        raise SiegeIndisponible()
    sieges = list(seance.salle.sieges.filter(id__in=siege_ids))
    reservation = Reservation.objects.create(seance=seance, canal=canal)
    bloquer_sieges(seance, sieges, reservation)
    return reservation


def places_encore_bloquees(reservation):
    """Vrai si toutes les places de la réservation lui appartiennent encore."""
    places = reservation.places.all()
    return places.exists() and all(p.statut == PlaceSeance.Statut.BLOQUEE for p in places)


def plan_de_salle(seance):
    """Données du plan de salle envoyées au navigateur en JSON toutes les 5 secondes."""
    liberer_places_expirees(seance)
    places = seance.places.select_related("siege").order_by("siege__rangee", "siege__numero")
    rangees = {}
    for p in places:
        rangees.setdefault(p.siege.rangee, []).append({
            "id": p.siege_id,
            "numero": p.siege.numero,
            "type": p.siege.type,
            "statut": p.statut_effectif,
        })
    libres = sum(1 for r in rangees.values() for s in r if s["statut"] == PlaceSeance.Statut.LIBRE)
    return {
        "seance": seance.id,
        "reservable": seance.est_reservable,
        "allees": seance.salle.liste_allees(),
        "libres": libres,
        "rangees": [{"nom": nom, "sieges": sieges} for nom, sieges in rangees.items()],
        "maj": timezone.now().isoformat(),
    }


def compter_places(seance):
    """Nombre de places libres, bloquées et vendues d'une séance."""
    maintenant = timezone.now()
    resultat = {"libres": 0, "bloquees": 0, "vendues": 0}
    for statut, fin in seance.places.values_list("statut", "fin_blocage"):
        if statut == PlaceSeance.Statut.VENDUE:
            resultat["vendues"] += 1
        elif statut == PlaceSeance.Statut.BLOQUEE and fin and fin >= maintenant:
            resultat["bloquees"] += 1
        else:
            resultat["libres"] += 1
    return resultat


def annuler_seance(seance):
    """E5-US2 : annule une séance ; les spectateurs sont prévenus par e-mail et remboursés."""
    from billetterie.services import prevenir_annulation
    from paiement.services import rembourser

    seance.statut = seance.Statut.ANNULEE
    seance.save(update_fields=["statut"])
    nb = 0
    for reservation in seance.reservations.filter(statut=Reservation.Statut.PAYEE):
        rembourser(reservation)
        reservation.statut = Reservation.Statut.ANNULEE
        reservation.save(update_fields=["statut"])
        prevenir_annulation(reservation)
        nb += 1
    return nb
