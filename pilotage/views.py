"""
Pilotage (EPIC E7) : remplissage par séance, ventes par canal et par créneau, export CSV.
Ces chiffres servent à mesurer les objectifs du dossier 1 (O1, O4, O6).
"""
import csv
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from billetterie.models import Billet
from catalogue.models import Seance
from grandcinema.acces import administrateur_requis


def periode(request):
    aujourdhui = timezone.localdate()
    try:
        debut = date.fromisoformat(request.GET.get("du", ""))
    except ValueError:
        debut = aujourdhui
    try:
        fin = date.fromisoformat(request.GET.get("au", ""))
    except ValueError:
        fin = debut + timedelta(days=6)
    return debut, max(fin, debut)


def lignes_remplissage(debut, fin):
    maintenant = timezone.now()
    seances = (Seance.objects.filter(debut__date__gte=debut, debut__date__lte=fin)
               .select_related("film", "salle")
               .annotate(capacite=Count("places", distinct=True),
                         vendues=Count("places", filter=Q(places__statut="vendue"), distinct=True),
                         vendues_site=Count("places", filter=Q(places__statut="vendue", places__reservation__canal="site"), distinct=True),
                         bloquees=Count("places", filter=Q(places__statut="bloquee", places__fin_blocage__gte=maintenant), distinct=True)))
    recettes = dict(Billet.objects.filter(place__seance__in=seances, place__statut="vendue")
                    .values_list("place__seance").annotate(total=Sum("prix")))
    lignes = []
    for s in seances:
        lignes.append({
            "seance": s,
            "debut": timezone.localtime(s.debut),
            "capacite": s.capacite,
            "vendues": s.vendues,
            "vendues_site": s.vendues_site,
            "vendues_guichet": s.vendues - s.vendues_site,
            "bloquees": s.bloquees,
            "taux": round(100 * s.vendues / s.capacite) if s.capacite else 0,
            "recette": recettes.get(s.id, Decimal("0")),
        })
    return lignes


@administrateur_requis
def tableau(request):
    debut, fin = periode(request)
    lignes = lignes_remplissage(debut, fin)
    capacite = sum(l["capacite"] for l in lignes)
    vendues = sum(l["vendues"] for l in lignes)
    site = sum(l["vendues_site"] for l in lignes)
    creneaux = defaultdict(lambda: {"capacite": 0, "vendues": 0})
    for l in lignes:
        c = creneaux[f"{l['debut']:%H}h"]
        c["capacite"] += l["capacite"]
        c["vendues"] += l["vendues"]
    creneaux = [{"heure": h, **v, "taux": round(100 * v["vendues"] / v["capacite"]) if v["capacite"] else 0}
                for h, v in sorted(creneaux.items())]
    return render(request, "pilotage/tableau.html", {
        "debut": debut, "fin": fin, "lignes": lignes, "creneaux": creneaux,
        "indicateurs": {
            "vendues": vendues,
            "taux": round(100 * vendues / capacite) if capacite else 0,
            "part_site": round(100 * site / vendues) if vendues else 0,
            "recette": sum((l["recette"] for l in lignes), Decimal("0")),
            "seances": len(lignes),
        },
        "objectif_en_ligne": settings.OBJECTIF_PART_EN_LIGNE,
        "objectif_atteint": vendues and round(100 * site / vendues) >= settings.OBJECTIF_PART_EN_LIGNE,
        "rafraichissement": settings.RAFRAICHISSEMENT_PILOTAGE_SECONDES,
    })


@administrateur_requis
def export_csv(request):
    """Export lisible dans un tableur (séparateur « ; » et encodage reconnu par Excel)."""
    debut, fin = periode(request)
    reponse = HttpResponse(content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = f'attachment; filename="remplissage_{debut}_{fin}.csv"'
    reponse.write("﻿")
    ecrivain = csv.writer(reponse, delimiter=";")
    ecrivain.writerow(["Date", "Heure", "Film", "Salle", "Statut", "Capacité", "Vendues", "Dont site", "Dont guichet",
                       "Bloquées", "Remplissage (%)", "Recette (€)"])
    for l in lignes_remplissage(debut, fin):
        s = l["seance"]
        ecrivain.writerow([f"{l['debut']:%d/%m/%Y}", f"{l['debut']:%H:%M}", s.film.titre, s.salle.nom, s.get_statut_display(),
                           l["capacite"], l["vendues"], l["vendues_site"], l["vendues_guichet"], l["bloquees"], l["taux"],
                           str(l["recette"]).replace(".", ",")])
    return reponse


# --- E8-US1 : anticiper les pics d'affluence du festival ------------------------------------------
SEUIL_ALERTE = 80          # % de places vendues…
DELAI_ALERTE = timedelta(days=3)  # … à 3 jours ou moins de la séance : il faut ouvrir une séance de plus
HORIZON_FESTIVAL = timedelta(days=90)  # séances suivies : jusqu'à 3 mois à l'avance (cible O6 : 4 semaines)


def ventes_festival(maintenant=None):
    """Pour chaque séance à venir d'un film du festival : places vendues jour après jour (cumul),
    depuis la première vente, et alerte si la séance est remplie à 80 % ou plus à 3 jours ou moins."""
    maintenant = maintenant or timezone.now()
    seances = list(Seance.objects.filter(film__festival=True, statut=Seance.Statut.PUBLIEE,
                                         debut__gt=maintenant, debut__lte=maintenant + HORIZON_FESTIVAL)
                   .select_related("film", "salle").annotate(capacite=Count("places", distinct=True))
                   .order_by("debut"))
    par_jour = defaultdict(dict)
    for ligne in (Billet.objects.filter(place__seance__in=seances, place__statut="vendue")
                  .annotate(jour=TruncDate("place__reservation__paiement__cree_le"))
                  .values("place__seance", "jour").annotate(n=Count("id"))):
        if ligne["jour"]:
            par_jour[ligne["place__seance"]][ligne["jour"]] = ligne["n"]
    jours_de_vente = sorted({j for ventes in par_jour.values() for j in ventes})
    premier = jours_de_vente[0] if jours_de_vente else timezone.localdate(maintenant)
    aujourdhui = timezone.localdate(maintenant)
    jours = [premier + timedelta(days=i) for i in range((aujourdhui - premier).days + 1)]
    lignes = []
    for s in seances:
        cumul, courbe = 0, []
        for jour in jours:
            cumul += par_jour[s.id].get(jour, 0)
            courbe.append({"jour": jour, "cumul": cumul, "hauteur": round(100 * cumul / s.capacite) if s.capacite else 0})
        taux = round(100 * cumul / s.capacite) if s.capacite else 0
        lignes.append({"seance": s, "debut": timezone.localtime(s.debut), "capacite": s.capacite, "vendues": cumul,
                       "taux": taux, "courbe": courbe,
                       "alerte": taux >= SEUIL_ALERTE and s.debut - maintenant <= DELAI_ALERTE})
    return lignes, jours


@administrateur_requis
def festival(request):
    lignes, jours = ventes_festival()
    return render(request, "pilotage/festival.html", {
        "lignes": lignes, "jours": jours, "alertes": [l for l in lignes if l["alerte"]],
        "seuil": SEUIL_ALERTE, "delai": DELAI_ALERTE.days,
    })
