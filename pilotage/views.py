"""
Pilotage (EPIC E7) : remplissage par séance, ventes par canal et par créneau, export CSV.
Ces chiffres servent à mesurer les objectifs du dossier 1 (O1, O4, O6).
"""
import csv
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
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
