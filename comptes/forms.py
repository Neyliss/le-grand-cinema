from django import forms
from django.contrib.auth import authenticate, password_validation
from django.utils.translation import gettext_lazy as _

from .services import est_spectateur_confirme, normaliser


class InscriptionForm(forms.Form):
    nom = forms.CharField(label=_("Nom"), max_length=100)
    email = forms.EmailField(label=_("Adresse e-mail"))
    mot_de_passe = forms.CharField(label=_("Mot de passe"), widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    confirmation = forms.CharField(label=_("Mot de passe (encore une fois)"), widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def clean_email(self):
        return normaliser(self.cleaned_data["email"])

    def clean(self):
        donnees = super().clean()
        if donnees.get("mot_de_passe") and donnees.get("mot_de_passe") != donnees.get("confirmation"):
            self.add_error("confirmation", _("Les deux mots de passe ne sont pas identiques."))
        elif donnees.get("mot_de_passe"):
            try:
                password_validation.validate_password(donnees["mot_de_passe"])
            except forms.ValidationError as erreur:
                self.add_error("mot_de_passe", erreur)
        return donnees


class ConnexionForm(forms.Form):
    email = forms.EmailField(label=_("Adresse e-mail"))
    mot_de_passe = forms.CharField(label=_("Mot de passe"), widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        self.utilisateur = None
        super().__init__(*args, **kwargs)

    def clean(self):
        donnees = super().clean()
        if self.errors:
            return donnees
        utilisateur = authenticate(self.request, username=normaliser(donnees["email"]), password=donnees["mot_de_passe"])
        if utilisateur is None:
            raise forms.ValidationError(_("Adresse e-mail ou mot de passe incorrect."))
        if not est_spectateur_confirme(utilisateur):
            raise forms.ValidationError(_("Confirmez d'abord votre adresse e-mail avec le lien reçu."))
        self.utilisateur = utilisateur
        return donnees
