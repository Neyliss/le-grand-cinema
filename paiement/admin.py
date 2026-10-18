from django.contrib import admin

from .models import Paiement


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ("reservation", "mode", "montant", "statut", "cree_le")
    list_filter = ("mode", "statut")
    readonly_fields = ("reservation", "mode", "reference_stripe", "montant", "cree_le")
