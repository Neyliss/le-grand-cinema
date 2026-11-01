"""
Données de démonstration : 10 salles (1 700 places), 3 films, 7 jours de séances,
des ventes déjà faites (site et guichet) et deux comptes du personnel.

    python manage.py charger_demo
    python manage.py charger_demo --reinitialiser   # efface d'abord les données existantes
"""
import random
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import Group, Permission, User
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from billetterie.models import Billet
from catalogue.models import Film, Salle, Seance, Tarif
from grandcinema.acces import GROUPE_ADMINISTRATEURS, GROUPE_AGENTS
from paiement.models import Paiement
from reservation.models import PlaceSeance, Reservation

AFFICHES = Path(__file__).resolve().parents[2] / "demo" / "affiches"

# nom, type, rangées, sièges par rangée, allées après les sièges n° : total 1 700 places
SALLES = [
    ("Salle 1", "premium", 13, 20, "4,16"), ("Salle 2", "standard", 11, 20, "4,16"),
    ("Salle 3", "standard", 10, 20, "4,16"), ("Salle 4", "standard", 9, 20, "4,16"),
    ("Salle 5", "standard", 10, 17, "4,13"), ("Salle 6", "standard", 10, 16, "4,12"),
    ("Salle 7", "standard", 10, 15, "3,12"), ("Salle 8", "standard", 10, 13, "3,10"),
    ("Salle 9", "standard", 10, 12, "2,10"), ("Salle 10", "vip", 10, 11, "2,9"),
]

FILMS = [
    ("Nuit Bleue", 112, "VF", "Tous publics", False, "nuit-bleue.png",
     "Un pianiste de jazz revient dans sa ville natale et retrouve le club où tout a commencé."),
    ("Les Rives du Jazz", 98, "VOST", "Tous publics", True, "les-rives-du-jazz.png",
     "Documentaire sur les grands clubs de jazz, de La Nouvelle-Orléans aux caves de Paris."),
    ("L'Horizon", 125, "VF", "Dès 12 ans", False, "l-horizon.png",
     "Une traversée en mer qui tourne mal oblige un équipage à faire des choix impossibles."),
]

# film, salle, heure, part des places déjà vendues
PROGRAMME = [
    ("Nuit Bleue", "Salle 3", "14:00", 0.40), ("Nuit Bleue", "Salle 3", "17:30", 0.75),
    ("Nuit Bleue", "Salle 3", "20:45", 0.55), ("L'Horizon", "Salle 5", "15:15", 0.45),
    ("L'Horizon", "Salle 5", "20:30", 0.95), ("Les Rives du Jazz", "Salle 1", "18:00", 0.65),
    ("Les Rives du Jazz", "Salle 1", "21:00", 1.00),
]

TARIFS = [("Plein", "10.00", 1), ("Réduit (étudiant)", "8.00", 2), ("Moins de 14 ans", "6.00", 3)]


SPECTATEUR_DEMO = "spectateur.demo@exemple.fr"


class Command(BaseCommand):
    help = "Charge des données de démonstration (salles, films, séances, ventes, comptes du personnel et spectateur)."

    def add_arguments(self, parser):
        parser.add_argument("--reinitialiser", action="store_true", help="Efface les données existantes avant le chargement.")
        parser.add_argument("--si-perime", action="store_true",
                            help="Recharge tout seulement si la programmation se termine dans moins de 3 jours (déploiement).")

    def handle(self, *args, **options):
        if options["si_perime"] and Film.objects.exists():
            if Seance.objects.filter(debut__gte=timezone.now() + timedelta(days=3)).exists():
                self.stdout.write("Programmation encore à jour : rien à recharger.")
                return
            options["reinitialiser"] = True
        if Film.objects.exists() and not options["reinitialiser"]:
            self.stdout.write(self.style.WARNING("Des données existent déjà. Utilisez --reinitialiser pour tout recharger."))
            return
        random.seed(2026)
        with transaction.atomic():
            if options["reinitialiser"]:
                self.vider()
            tarifs = [Tarif.objects.create(libelle=l, prix=Decimal(p), ordre=o) for l, p, o in TARIFS]
            salles = {}
            for nom, type_, rangees, par_rangee, allees in SALLES:
                salle = Salle.objects.create(nom=nom, type=type_, allees=allees)
                salle.generer_sieges(rangees, par_rangee)
                salles[nom] = salle
            films = {}
            for titre, duree, version, classification, festival, affiche, synopsis in FILMS:
                film = Film(titre=titre, duree=duree, version=version, classification=classification,
                            festival=festival, synopsis=synopsis)
                with open(AFFICHES / affiche, "rb") as f:
                    film.affiche.save(affiche, File(f), save=False)
                film.save()
                films[titre] = film
            nb_seances = nb_billets = 0
            aujourdhui = timezone.localdate()
            for jour in range(7):
                date = aujourdhui + timedelta(days=jour)
                for titre, salle, heure, remplissage in PROGRAMME:
                    h, m = map(int, heure.split(":"))
                    debut = timezone.make_aware(datetime.combine(date, time(h, m)))
                    seance = Seance.objects.create(film=films[titre], salle=salles[salle], debut=debut,
                                                   langue="anglais" if films[titre].version == "VOST" else "français")
                    part = remplissage if jour == 0 else max(0.15, min(1.0, remplissage + random.uniform(-0.35, 0.05)))
                    nb_billets += self.vendre(seance, part, tarifs)
                    nb_seances += 1
            self.creer_comptes()
        self.stdout.write(self.style.SUCCESS(
            f"{len(SALLES)} salles ({sum(r * s for _, _, r, s, _ in SALLES)} places), {len(films)} films, "
            f"{nb_seances} séances et {nb_billets} billets vendus chargés."))
        self.stdout.write("Comptes de démonstration (site de démonstration uniquement) :")
        self.stdout.write("  administrateur : admin / admin-gc-2026")
        self.stdout.write("  agent d'accueil : agent / agent-gc-2026")
        self.stdout.write(f"  spectateur : {SPECTATEUR_DEMO} / spectateur-gc-2026")

    def vider(self):
        from fidelite.models import Abonnement, FormuleAbonnement

        Abonnement.objects.all().delete()
        FormuleAbonnement.objects.all().delete()
        Billet.objects.all().delete()
        Paiement.objects.all().delete()
        PlaceSeance.objects.all().delete()
        Reservation.objects.all().delete()
        Seance.objects.all().delete()
        Film.objects.all().delete()
        Salle.objects.all().delete()
        Tarif.objects.all().delete()

    def vendre(self, seance, part, tarifs):
        """Simule des ventes passées : groupes de 1 à 4 places, sur le site ou au guichet."""
        places = list(seance.places.select_related("siege"))
        a_vendre = int(len(places) * part)
        random.shuffle(places)
        places = sorted(places[:a_vendre], key=lambda p: (p.siege.rangee, p.siege.numero))
        billets, paiements_dates = [], []
        i = 0
        while i < len(places):
            groupe = places[i:i + random.randint(1, 4)]
            i += len(groupe)
            canal = Reservation.Canal.SITE if random.random() < 0.55 else Reservation.Canal.GUICHET
            reservation = Reservation.objects.create(
                seance=seance, canal=canal, statut=Reservation.Statut.PAYEE,
                nom="Spectateur" if canal == Reservation.Canal.SITE else "",
                email="spectateur@exemple.fr" if canal == Reservation.Canal.SITE else "")
            montant = Decimal("0")
            for place in groupe:
                place.statut, place.reservation = PlaceSeance.Statut.VENDUE, reservation
                tarif = random.choices(tarifs, weights=[6, 3, 1])[0]
                billets.append(Billet(place=place, tarif=tarif, prix=tarif.prix))
                montant += tarif.prix
            mode = Paiement.Mode.CARTE_EN_LIGNE if canal == Reservation.Canal.SITE else random.choice(
                [Paiement.Mode.GUICHET_CARTE, Paiement.Mode.GUICHET_ESPECES])
            paiement = Paiement.objects.create(reservation=reservation, mode=mode, montant=montant,
                                               reference_stripe=f"demo-{reservation.reference}" if canal == Reservation.Canal.SITE else "")
            # Ventes étalées sur les 14 derniers jours : le tableau du festival (E8) montre leur progression.
            paiements_dates.append((paiement.id, timezone.now() - timedelta(days=random.randint(0, 13), minutes=random.randint(0, 600))))
        for paiement_id, date in paiements_dates:
            Paiement.objects.filter(pk=paiement_id).update(cree_le=date)
        PlaceSeance.objects.bulk_update(places, ["statut", "reservation"])
        Billet.objects.bulk_create(billets)
        return len(billets)

    def creer_comptes(self):
        agents, _ = Group.objects.get_or_create(name=GROUPE_AGENTS)
        administrateurs, _ = Group.objects.get_or_create(name=GROUPE_ADMINISTRATEURS)
        administrateurs.permissions.set(Permission.objects.filter(
            content_type__app_label__in=["catalogue", "reservation", "paiement", "billetterie", "fidelite"]))
        agents.permissions.set(Permission.objects.filter(codename__startswith="view_",
                                                         content_type__app_label__in=["catalogue", "reservation"]))
        if not User.objects.filter(username="admin").exists():
            admin = User.objects.create_superuser("admin", "admin@exemple.fr", "admin-gc-2026", first_name="Direction")
            admin.groups.add(administrateurs)
        if not User.objects.filter(username="agent").exists():
            agent = User.objects.create_user("agent", "agent@exemple.fr", "agent-gc-2026", first_name="Accueil 1", is_staff=True)
            agent.groups.add(agents)
        self.creer_spectateur_demo()

    def creer_spectateur_demo(self):
        """Compte spectateur confirmé (E9-US1), avec trois réservations payées sur le site."""
        from comptes.models import Profil
        from comptes.services import GROUPE_SPECTATEURS

        spectateur = User.objects.filter(username=SPECTATEUR_DEMO).first()
        if spectateur is None:
            spectateur = User.objects.create_user(SPECTATEUR_DEMO, SPECTATEUR_DEMO, "spectateur-gc-2026", first_name="Camille")
            Profil.objects.create(utilisateur=spectateur, email_confirme=True)
            spectateur.groups.add(Group.objects.get_or_create(name=GROUPE_SPECTATEURS)[0])
        spectateur.profil.accepte_offres = True
        spectateur.profil.save(update_fields=["accepte_offres"])
        self.creer_fidelite(spectateur)
        # Une réservation par film, à des jours différents
        ids, films = [], set()
        for jour in (0, 2, 4):
            date = timezone.localdate() + timedelta(days=jour)
            reservation = (Reservation.objects.filter(canal=Reservation.Canal.SITE, statut=Reservation.Statut.PAYEE,
                                                      seance__debut__date=date).exclude(seance__film__in=films)
                           .order_by("seance__debut").first())
            if reservation:
                ids.append(reservation.id)
                films.add(reservation.seance.film_id)
        Reservation.objects.filter(id__in=ids).update(compte=spectateur, nom="Camille", email=SPECTATEUR_DEMO)

    def creer_fidelite(self, spectateur):
        """E10-US1 : une formule de carte, le tarif « Abonné » et une carte entamée pour le spectateur."""
        from fidelite.models import Abonnement, FormuleAbonnement

        formule, _ = FormuleAbonnement.objects.get_or_create(libelle="Carte 10 places", defaults={"nb_places": 10, "prix": Decimal("75.00")})
        Tarif.objects.get_or_create(libelle="Abonné", defaults={"prix": Decimal("0.00"), "reserve_abonnes": True, "ordre": 4})
        if not Abonnement.objects.filter(compte=spectateur).exists():
            Abonnement.objects.create(compte=spectateur, formule=formule, prix=formule.prix, places_restantes=7,
                                      statut=Abonnement.Statut.ACTIVE, active_le=timezone.now() - timedelta(days=20))
