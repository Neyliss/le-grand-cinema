"""
Module reservation : plan de salle, blocage et libération des sièges, réservations (EPICs E2 et E3).
"""
import secrets
from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

ALPHABET_REFERENCE = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sans O/0 ni I/1 pour éviter les confusions


def generer_reference():
    return "GC-" + "".join(secrets.choice(ALPHABET_REFERENCE) for _ in range(5))


def generer_jeton():
    return secrets.token_urlsafe(24)


class Reservation(models.Model):
    class Canal(models.TextChoices):
        SITE = "site", _("site")
        GUICHET = "guichet", _("guichet")

    class Statut(models.TextChoices):
        ATTENTE = "attente", _("en attente")
        PAYEE = "payee", _("payée")
        ANNULEE = "annulee", _("annulée")

    reference = models.CharField("référence", max_length=12, unique=True, default=generer_reference)
    # Jeton secret placé dans le lien du billet : seul le spectateur qui a reçu l'e-mail peut l'ouvrir.
    jeton = models.CharField(max_length=40, default=generer_jeton, editable=False)
    # Lien direct vers la séance (pratique pour les statistiques, même après libération des places).
    seance = models.ForeignKey("catalogue.Seance", on_delete=models.PROTECT, related_name="reservations")
    nom = models.CharField(max_length=100, blank=True)
    email = models.EmailField("e-mail", blank=True)
    canal = models.CharField(max_length=10, choices=Canal.choices, default=Canal.SITE)
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.ATTENTE)
    cree_le = models.DateTimeField("créée le", auto_now_add=True)
    billets_pdf = models.FileField(upload_to="billets/", blank=True)

    class Meta:
        ordering = ["-cree_le"]
        verbose_name = "réservation"

    def __str__(self):
        return self.reference

    def save(self, *args, **kwargs):
        # La référence est tirée au hasard : si elle est déjà prise, on en tire une autre.
        if self._state.adding:
            while Reservation.objects.filter(reference=self.reference).exists():
                self.reference = generer_reference()
        super().save(*args, **kwargs)

    @property
    def est_payee(self):
        return self.statut == self.Statut.PAYEE

    def billets(self):
        from billetterie.models import Billet

        return Billet.objects.filter(place__reservation=self).select_related("place__siege", "tarif")

    @property
    def montant(self):
        return sum((b.prix for b in self.billets()), Decimal("0.00"))

    def fin_blocage(self):
        place = self.places.filter(statut=PlaceSeance.Statut.BLOQUEE).order_by("fin_blocage").first()
        return place.fin_blocage if place else None


class PlaceSeanceQuerySet(models.QuerySet):
    def disponibles(self):
        """Places libres, ou bloquées dont le délai de 10 minutes est dépassé."""
        maintenant = timezone.now()
        return self.filter(Q(statut=PlaceSeance.Statut.LIBRE)
                           | Q(statut=PlaceSeance.Statut.BLOQUEE, fin_blocage__lt=maintenant))

    def bloquees_expirees(self):
        return self.filter(statut=PlaceSeance.Statut.BLOQUEE, fin_blocage__lt=timezone.now())


class PlaceSeance(models.Model):
    """Un siège pour une séance donnée. C'est le stock unique partagé par le site et le guichet."""

    class Statut(models.TextChoices):
        LIBRE = "libre", _("libre")
        BLOQUEE = "bloquee", _("bloquée")
        VENDUE = "vendue", _("vendue")

    seance = models.ForeignKey("catalogue.Seance", on_delete=models.CASCADE, related_name="places")
    siege = models.ForeignKey("catalogue.Siege", on_delete=models.PROTECT, related_name="places")
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.LIBRE)
    reservation = models.ForeignKey(Reservation, null=True, blank=True, on_delete=models.SET_NULL, related_name="places")
    fin_blocage = models.DateTimeField(null=True, blank=True)

    objects = PlaceSeanceQuerySet.as_manager()

    class Meta:
        verbose_name = "place de séance"
        verbose_name_plural = "places de séance"
        ordering = ["siege__rangee", "siege__numero"]
        constraints = [
            # Dernière protection contre la double vente : la base refuse deux places
            # pour le même siège dans la même séance (contrainte {unique} de la figure 9).
            models.UniqueConstraint(fields=["seance", "siege"], name="place_unique_par_seance"),
        ]

    def __str__(self):
        return f"{self.siege} — {self.seance}"

    @property
    def statut_effectif(self):
        """Statut vu par les spectateurs : un blocage expiré compte comme une place libre."""
        if self.statut == self.Statut.BLOQUEE and self.fin_blocage and self.fin_blocage < timezone.now():
            return self.Statut.LIBRE
        return self.statut
