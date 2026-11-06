"""Connexion protégée contre les essais de mots de passe en série.

Après CONNEXION_ESSAIS_MAX mots de passe faux pour un même identifiant, toute connexion à cet
identifiant est refusée pendant CONNEXION_BLOCAGE_SECONDES, même avec le bon mot de passe.
Cela vaut pour le site, l'administration et l'API : tous passent par ce contrôle.
Le compteur est gardé dans le cache de Django (en mémoire, propre à chaque processus du serveur).
"""
import hashlib

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.cache import cache


def cle_compteur(identifiant):
    # L'identifiant est haché : aucune adresse e-mail n'est gardée en clair dans le cache
    return "echecs-connexion:" + hashlib.sha256(str(identifiant).strip().lower().encode()).hexdigest()


def identifiant_bloque(identifiant):
    return cache.get(cle_compteur(identifiant), 0) >= settings.CONNEXION_ESSAIS_MAX


class ConnexionLimitee(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(get_user_model().USERNAME_FIELD)
        if username is None or password is None:
            return None
        cle = cle_compteur(username)
        if identifiant_bloque(username):
            return None
        utilisateur = super().authenticate(request, username=username, password=password, **kwargs)
        if utilisateur is None:
            cache.add(cle, 0, settings.CONNEXION_BLOCAGE_SECONDES)
            try:
                cache.incr(cle)
            except ValueError:  # le compteur vient d'expirer
                cache.set(cle, 1, settings.CONNEXION_BLOCAGE_SECONDES)
        else:
            cache.delete(cle)
        return utilisateur
