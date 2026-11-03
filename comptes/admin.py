from django.contrib import admin

from .models import Profil


@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "email_confirme", "cree_le")
    list_filter = ("email_confirme",)
    search_fields = ("utilisateur__email",)
