"""Renvoie les visites directes du serveur vers l'adresse publique du site, en HTTPS."""
from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponseRedirect


class RedirectionVersSitePublic:
    """Le serveur Elastic Beanstalk répond aussi en HTTP sur sa propre adresse. Là, les cookies
    sécurisés ne fonctionnent pas (pas de connexion possible) : le visiteur est donc renvoyé vers
    l'adresse publique CloudFront (SITE_URL), qui est en HTTPS."""

    def __init__(self, get_response):
        self.get_response = get_response
        adresse = urlsplit(settings.SITE_URL)
        self.actif = adresse.scheme == "https"
        self.hote_public = adresse.netloc

    def __call__(self, request):
        if self.actif and not request.is_secure() and request.get_host() != self.hote_public:
            return HttpResponseRedirect(settings.SITE_URL.rstrip("/") + request.get_full_path())
        return self.get_response(request)
