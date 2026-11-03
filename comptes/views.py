"""Pages du compte spectateur (E9-US1) : créer un compte, confirmer l'adresse, se connecter,
retrouver ses réservations, supprimer son compte."""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from .forms import ConnexionForm, InscriptionForm
from .services import (CompteExistant, confirmer, creer_compte, lien_confirmation, rattacher_reservations,
                       reservations_du_compte, supprimer_compte)


def inscription(request):
    form = InscriptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            utilisateur = creer_compte(form.cleaned_data["email"], form.cleaned_data["mot_de_passe"], form.cleaned_data["nom"],
                                       accepte_offres=form.cleaned_data["accepte_offres"])
        except CompteExistant:
            form.add_error("email", _("Un compte existe déjà avec cette adresse."))
        else:
            # Site de démonstration (aucun e-mail réellement envoyé) : le lien est affiché à l'écran.
            lien = lien_confirmation(utilisateur) if settings.PAIEMENT_DEMO else None
            return render(request, "comptes/inscription_envoyee.html", {"email": utilisateur.email, "lien_demo": lien})
    return render(request, "comptes/inscription.html", {"form": form})


@require_GET
def confirmation(request, jeton):
    utilisateur = confirmer(jeton)
    if utilisateur is None:
        messages.error(request, _("Ce lien de confirmation n'est plus valable. Créez à nouveau votre compte."))
        return redirect("comptes:inscription")
    login(request, utilisateur, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, _("Adresse confirmée : bienvenue ! Vos réservations passées ont été rattachées à votre compte."))
    return redirect("comptes:mon_compte")


def connexion(request):
    form = ConnexionForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        login(request, form.utilisateur)
        rattacher_reservations(form.utilisateur)  # réservations faites sans être connecté, avec la même adresse
        suite = request.GET.get("next", "")
        return redirect(suite if suite.startswith("/") and not suite.startswith("//") else "comptes:mon_compte")
    return render(request, "comptes/connexion.html", {"form": form})


@require_POST
def deconnexion(request):
    logout(request)
    return redirect("catalogue:programmation")


@login_required
@require_GET
def mon_compte(request):
    from fidelite.services import carte_active

    return render(request, "comptes/mon_compte.html", {
        "reservations": reservations_du_compte(request.user),
        "carte": carte_active(request.user),
    })


@login_required
@require_POST
def preferences(request):
    """E10-US1 : le spectateur choisit lui-même de recevoir, ou non, les offres."""
    profil = getattr(request.user, "profil", None)
    if profil is not None:
        profil.accepte_offres = request.POST.get("accepte_offres") == "on"
        profil.save(update_fields=["accepte_offres"])
        messages.success(request, _("Votre choix est enregistré."))
    return redirect("comptes:mon_compte")


@login_required
def suppression(request):
    if request.method == "POST":
        supprimer_compte(request.user)
        logout(request)
        messages.success(request, _("Votre compte et vos données personnelles ont été supprimés."))
        return redirect("catalogue:programmation")
    return render(request, "comptes/suppression.html")
