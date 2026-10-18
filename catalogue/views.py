"""Pages publiques (EPIC E1) : programmation par jour, festival de Jazz, infos pratiques."""
from datetime import date, timedelta

from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from .models import Film, Seance, Tarif


def avec_places_libres(seances):
    """Ajoute à chaque séance son nombre de places libres (un blocage expiré compte comme libre)."""
    maintenant = timezone.now()
    libres = Count("places", filter=Q(places__statut="libre")
                   | Q(places__statut="bloquee", places__fin_blocage__lt=maintenant))
    return seances.select_related("film", "salle").annotate(nb_libres=libres)


def regrouper_par_film(seances):
    films = {}
    for seance in seances:
        films.setdefault(seance.film, []).append(seance)
    return sorted(films.items(), key=lambda item: item[0].id)


def programmation(request):
    """E1-US1 : les films du jour avec leurs horaires et leurs places libres, sans compte."""
    aujourdhui = timezone.localdate()
    jours = [aujourdhui + timedelta(days=i) for i in range(7)]
    try:
        jour = date.fromisoformat(request.GET.get("jour", ""))
    except ValueError:
        jour = aujourdhui
    if jour not in jours:
        jour = aujourdhui
    seances = avec_places_libres(Seance.objects.a_venir().du_jour(jour))
    return render(request, "catalogue/programmation.html", {
        "jours": jours,
        "jour": jour,
        "aujourdhui": aujourdhui,
        "films": regrouper_par_film(seances),
    })


def festival(request):
    """Séances des films du festival de Jazz, sur les 30 prochains jours."""
    fin = timezone.now() + timedelta(days=30)
    seances = avec_places_libres(Seance.objects.a_venir().filter(film__festival=True, debut__lt=fin))
    jours = {}
    for seance in seances:
        jours.setdefault(timezone.localdate(seance.debut), []).append(seance)
    return render(request, "catalogue/festival.html", {
        "jours": sorted(jours.items()),
        "films": Film.objects.filter(festival=True),
    })


def infos(request):
    return render(request, "catalogue/infos.html", {"tarifs": Tarif.objects.filter(actif=True)})
