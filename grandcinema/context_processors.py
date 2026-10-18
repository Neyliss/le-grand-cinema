"""Données ajoutées automatiquement à toutes les pages."""
from django.conf import settings
from django.urls import translate_url


def langues(request):
    """Sélecteur FR / EN : adresse de la page affichée dans chaque langue.

    Avec i18n_patterns, la langue se lit dans l'adresse : /infos/ en français, /en/infos/ en
    anglais. Chaque bouton est donc un simple lien vers la même page dans l'autre langue.
    """
    page = request.get_full_path()
    return {"liens_langues": [(code, translate_url(page, code)) for code, _nom in settings.LANGUAGES]}
