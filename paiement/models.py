"""
Module paiement : dialogue avec Stripe (composant C8), confirmations et remboursements (EPIC E3).
Aucune donnée de carte n'est enregistrée ici : seule la référence Stripe est conservée.
"""
from django.db import models


class Paiement(models.Model):
    class Mode(models.TextChoices):
        CARTE_EN_LIGNE = "carte_en_ligne", "Carte en ligne (Stripe)"
        GUICHET_CARTE = "guichet_carte", "Guichet — carte (terminal)"
        GUICHET_ESPECES = "guichet_especes", "Guichet — espèces"

    class Statut(models.TextChoices):
        REUSSI = "reussi", "Réussi"
        ECHOUE = "echoue", "Échoué"
        REMBOURSE = "rembourse", "Remboursé"

    # Une réservation est réglée par un paiement (relation « réglée par » du diagramme)
    reservation = models.OneToOneField("reservation.Reservation", on_delete=models.PROTECT, related_name="paiement")
    mode = models.CharField(max_length=20, choices=Mode.choices)
    reference_stripe = models.CharField("référence Stripe", max_length=255, blank=True)
    montant = models.DecimalField(max_digits=8, decimal_places=2)
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.REUSSI)
    cree_le = models.DateTimeField("créé le", auto_now_add=True)

    class Meta:
        ordering = ["-cree_le"]

    def __str__(self):
        return f"{self.reservation} — {self.montant} € — {self.get_mode_display()}"
