"""
Module billetterie : billets avec QR code, envoi par e-mail, contrôle à l'entrée (EPICs E4 et E6).
"""
import secrets

from django.db import models


def generer_code_qr():
    return secrets.token_urlsafe(12)


class Billet(models.Model):
    # Un billet est émis pour une place précise (relation « pour » du diagramme de classes)
    place = models.OneToOneField("reservation.PlaceSeance", on_delete=models.CASCADE, related_name="billet")
    tarif = models.ForeignKey("catalogue.Tarif", on_delete=models.PROTECT, related_name="billets")
    # Prix copié au moment de la vente : si le tarif change plus tard, le billet garde son prix.
    prix = models.DecimalField(max_digits=6, decimal_places=2)
    code_qr = models.CharField("code QR", max_length=32, unique=True, default=generer_code_qr)
    utilise_le = models.DateTimeField("utilisé le", null=True, blank=True)

    class Meta:
        ordering = ["place__siege__rangee", "place__siege__numero"]

    def __str__(self):
        return f"Billet {self.place.siege} — {self.code_qr}"

    @property
    def reservation(self):
        return self.place.reservation

    @property
    def est_valide(self):
        """Valide si la place est vendue, la réservation payée et le billet pas encore utilisé."""
        r = self.place.reservation
        return (self.place.statut == "vendue" and r is not None and r.est_payee
                and self.utilise_le is None and r.seance.statut == "publiee")
