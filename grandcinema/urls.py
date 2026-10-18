"""Adresses du site. Les pages publiques existent en français (/) et en anglais (/en/)."""
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from paiement.views import webhook_stripe

admin.site.site_header = "Le Grand Cinéma — administration"
admin.site.site_title = "Le Grand Cinéma"
admin.site.index_title = "Programmation, salles et tarifs"

urlpatterns = [
    path("admin/", admin.site.urls),
    # Confirmation signée envoyée par Stripe (sans préfixe de langue)
    path("webhooks/stripe/", webhook_stripe, name="webhook_stripe"),
    # Espaces du personnel (en français uniquement)
    path("guichet/", include("guichet.urls")),
    path("controle/", include("billetterie.urls_controle")),
    path("pilotage/", include("pilotage.urls")),
]

# Pages publiques : / en français, /en/ en anglais. La langue se lit dans l'adresse ;
# le sélecteur FR / EN mène à la même page dans l'autre langue (grandcinema/context_processors.py).
urlpatterns += i18n_patterns(
    path("", include("catalogue.urls")),
    path("reservation/", include("reservation.urls")),
    path("paiement/", include("paiement.urls")),
    path("billet/", include("billetterie.urls")),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
