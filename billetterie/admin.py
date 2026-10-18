from django.contrib import admin

from .models import Billet


@admin.register(Billet)
class BilletAdmin(admin.ModelAdmin):
    list_display = ("code_qr", "place", "tarif", "prix", "utilise_le")
    search_fields = ("code_qr", "place__reservation__reference")
    readonly_fields = ("place", "tarif", "prix", "code_qr")
