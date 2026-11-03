from django.conf import settings
from django.contrib import admin, messages

from .models import Abonnement, FormuleAbonnement, Offre
from .services import destinataires_offres, envoyer_offre


@admin.register(FormuleAbonnement)
class FormuleAbonnementAdmin(admin.ModelAdmin):
    list_display = ("libelle", "nb_places", "prix", "actif")
    list_editable = ("prix", "actif")


@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ("reference", "compte", "formule", "places_restantes", "statut", "active_le")
    list_filter = ("statut", "formule")
    search_fields = ("reference", "compte__email")
    readonly_fields = ("reference", "compte", "formule", "prix", "statut", "reference_stripe", "active_le")


@admin.register(Offre)
class OffreAdmin(admin.ModelAdmin):
    list_display = ("titre", "envoyee_le", "nb_destinataires")
    readonly_fields = ("envoyee_le", "nb_destinataires")
    actions = ["envoyer"]

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = {**(extra_context or {}), "subtitle": f"{len(destinataires_offres())} spectateur(s) ont accepté les offres"}
        return super().changeform_view(request, object_id, form_url, extra_context)

    @admin.action(description="Envoyer aux spectateurs qui ont accepté les offres")
    def envoyer(self, request, queryset):
        deja_envoyees = queryset.filter(envoyee_le__isnull=False).count()
        for offre in list(queryset.filter(envoyee_le__isnull=True)):
            nb = envoyer_offre(offre, settings.SITE_URL)
            self.message_user(request, f"« {offre.titre} » envoyée à {nb} spectateur(s).", messages.SUCCESS)
        if deja_envoyees:
            self.message_user(request, f"{deja_envoyees} offre(s) déjà envoyée(s) : pas de second envoi.", messages.WARNING)
