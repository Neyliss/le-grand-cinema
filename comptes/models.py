"""
Module comptes (EPIC E9) : le compte spectateur est facultatif. Réserver sans compte reste possible.

Un spectateur est un utilisateur Django dont l'identifiant est son adresse e-mail. Son profil
indique s'il a confirmé son adresse : tant que ce n'est pas fait, il ne peut pas se connecter et
ses anciennes réservations ne lui sont pas rattachées (personne ne peut s'approprier celles d'un autre).
"""
from django.conf import settings
from django.db import models


class Profil(models.Model):
    utilisateur = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profil")
    email_confirme = models.BooleanField("adresse e-mail confirmée", default=False)
    cree_le = models.DateTimeField("créé le", auto_now_add=True)

    class Meta:
        verbose_name = "profil spectateur"
        verbose_name_plural = "profils spectateurs"

    def __str__(self):
        return self.utilisateur.email
