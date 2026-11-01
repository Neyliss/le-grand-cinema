"""
Module fidelite (EPIC E10) : cartes d'abonnement et offres réservées aux habitués.

La direction crée elle-même, dans l'administration, les formules de carte (ex. « Carte 10 places »),
le tarif « abonné » (catalogue.Tarif, case « réservé aux abonnés ») et les offres à envoyer.
"""
from django.conf import settings
from django.db import models

from reservation.models import generer_reference


class FormuleAbonnement(models.Model):
    libelle = models.CharField("libellé", max_length=60)
    nb_places = models.PositiveSmallIntegerField("nombre de places", default=10)
    prix = models.DecimalField(max_digits=6, decimal_places=2)
    actif = models.BooleanField("en vente", default=True)

    class Meta:
        ordering = ["prix"]
        verbose_name = "formule d'abonnement"
        verbose_name_plural = "formules d'abonnement"

    def __str__(self):
        return f"{self.libelle} ({self.nb_places} places, {self.prix} €)"


class Abonnement(models.Model):
    """Une carte achetée par un spectateur. Elle est active une fois payée."""

    class Statut(models.TextChoices):
        ATTENTE = "attente", "en attente de paiement"
        ACTIVE = "active", "active"

    reference = models.CharField("référence", max_length=12, unique=True, default=generer_reference)
    # Si le compte est supprimé (RGPD), la carte reste pour la comptabilité, sans lien avec la personne.
    compte = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="abonnements")
    formule = models.ForeignKey(FormuleAbonnement, on_delete=models.PROTECT, related_name="abonnements")
    prix = models.DecimalField(max_digits=6, decimal_places=2)
    # Nombre positif imposé par la base de données : une carte ne peut pas descendre sous zéro.
    places_restantes = models.PositiveSmallIntegerField("places restantes", default=0)
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.ATTENTE)
    reference_stripe = models.CharField("référence Stripe", max_length=255, blank=True)
    cree_le = models.DateTimeField("créée le", auto_now_add=True)
    active_le = models.DateTimeField("payée le", null=True, blank=True)

    class Meta:
        ordering = ["-cree_le"]
        verbose_name = "carte d'abonnement"
        verbose_name_plural = "cartes d'abonnement"

    def __str__(self):
        return f"{self.reference} — {self.formule.libelle}"


class Offre(models.Model):
    """Offre réservée aux habitués, écrite par la direction et envoyée depuis l'administration."""

    titre = models.CharField(max_length=120)
    message = models.TextField()
    envoyee_le = models.DateTimeField("envoyée le", null=True, blank=True)
    nb_destinataires = models.PositiveIntegerField("nombre de destinataires", default=0)

    class Meta:
        ordering = ["-id"]
        verbose_name = "offre"

    def __str__(self):
        return self.titre
