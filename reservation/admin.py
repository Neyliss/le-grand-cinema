from django.contrib import admin

from .models import PlaceSeance, Reservation


class PlaceInline(admin.TabularInline):
    model = PlaceSeance
    extra = 0
    fields = ("siege", "statut", "fin_blocage")
    readonly_fields = fields
    can_delete = False


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("reference", "seance", "nom", "email", "canal", "statut", "cree_le")
    list_filter = ("statut", "canal")
    search_fields = ("reference", "nom", "email")
    readonly_fields = ("reference", "seance", "canal", "cree_le", "billets_pdf")
    inlines = [PlaceInline]
