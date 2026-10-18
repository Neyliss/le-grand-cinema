"""
Administration (EPIC E5) : l'interface d'administration fournie par Django évite de
développer un back-office. Les administrateurs y gèrent films, salles, tarifs et séances.
"""
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from reservation.services import annuler_seance, compter_places

from .models import Film, Salle, Seance, Siege, Tarif


@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = ("titre", "duree_affichee", "version", "classification", "festival", "apercu")
    list_filter = ("version", "festival")
    search_fields = ("titre",)

    @admin.display(description="affiche")
    def apercu(self, film):
        if film.affiche:
            return format_html('<img src="{}" style="height:48px;border-radius:4px">', film.affiche.url)
        return "—"


class SiegeInline(admin.TabularInline):
    model = Siege
    extra = 0
    fields = ("rangee", "numero", "type")
    classes = ("collapse",)


@admin.register(Salle)
class SalleAdmin(admin.ModelAdmin):
    list_display = ("nom", "type", "capacite")
    inlines = [SiegeInline]


@admin.register(Tarif)
class TarifAdmin(admin.ModelAdmin):
    list_display = ("libelle", "prix", "actif", "ordre")
    list_editable = ("prix", "actif", "ordre")


@admin.register(Seance)
class SeanceAdmin(admin.ModelAdmin):
    list_display = ("film", "salle", "debut", "statut", "remplissage")
    list_filter = ("statut", "salle", "film", ("debut", admin.DateFieldListFilter))
    date_hierarchy = "debut"
    actions = ["annuler"]

    def get_readonly_fields(self, request, obj=None):
        # La salle ne change plus une fois les places créées
        return ("salle",) if obj else ()

    @admin.display(description="remplissage")
    def remplissage(self, seance):
        c = compter_places(seance)
        total = sum(c.values()) or 1
        return f"{c['vendues']} / {total} ({round(100 * c['vendues'] / total)} %)"

    @admin.action(description="Annuler les séances choisies (spectateurs prévenus et remboursés)")
    def annuler(self, request, queryset):
        nb_seances = nb_resa = 0
        for seance in queryset.exclude(statut=Seance.Statut.ANNULEE):
            nb_resa += annuler_seance(seance)
            nb_seances += 1
        self.message_user(request, f"{nb_seances} séance(s) annulée(s), {nb_resa} réservation(s) remboursée(s) et prévenue(s).",
                          messages.SUCCESS)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change and obj.debut < timezone.now():
            self.message_user(request, "Attention : cette séance est dans le passé.", messages.WARNING)
