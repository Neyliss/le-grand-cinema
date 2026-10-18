"""Droits d'accès du personnel (comptes du système d'authentification de Django).

- Agents d'accueil : guichet et contrôle à l'entrée (compte « membre du personnel »).
- Administrateurs : en plus, pilotage et administration de la programmation.
"""
from django.contrib.auth.decorators import user_passes_test

GROUPE_AGENTS = "Agents d'accueil"
GROUPE_ADMINISTRATEURS = "Administrateurs"


def est_agent(user):
    return user.is_active and user.is_staff


def est_administrateur(user):
    return user.is_active and (user.is_superuser or user.groups.filter(name=GROUPE_ADMINISTRATEURS).exists())


agent_requis = user_passes_test(est_agent, login_url="admin:login")
administrateur_requis = user_passes_test(est_administrateur, login_url="admin:login")
