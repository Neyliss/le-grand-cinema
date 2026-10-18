"""
Module catalogue : films, salles, sièges, tarifs et séances (EPICs E1 et E5).

Les classes reprennent le diagramme de classes du dossier 3 (figure 9).
Chaque classe devient une table de la base grâce à l'ORM de Django.
"""
from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Film(models.Model):
    class Version(models.TextChoices):
        VF = "VF", "VF"
        VOST = "VOST", "VOST"

    titre = models.CharField(max_length=120)
    duree = models.PositiveSmallIntegerField("durée (minutes)")
    version = models.CharField(max_length=4, choices=Version.choices, default=Version.VF)
    classification = models.CharField(max_length=40, default="Tous publics")
    synopsis = models.TextField(blank=True)
    affiche = models.ImageField(upload_to="affiches/", blank=True)
    festival = models.BooleanField("film du festival de Jazz", default=False)

    class Meta:
        ordering = ["titre"]

    def __str__(self):
        return self.titre

    @property
    def duree_affichee(self):
        """Durée lisible : 112 minutes -> « 1 h 52 »."""
        heures, minutes = divmod(self.duree, 60)
        return f"{heures} h {minutes:02d}" if heures else f"{minutes} min"


class Salle(models.Model):
    class Type(models.TextChoices):
        STANDARD = "standard", "Standard"
        PREMIUM = "premium", "Premium"
        VIP = "vip", "VIP"

    nom = models.CharField(max_length=40, unique=True)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.STANDARD)
    allees = models.CharField(
        "allées après les sièges n°",
        max_length=40,
        blank=True,
        help_text="Numéros de siège suivis d'une allée, séparés par des virgules (ex. : 4,16).",
    )

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom

    @property
    def capacite(self):
        return self.sieges.count()

    def liste_allees(self):
        return [int(n) for n in self.allees.split(",") if n.strip().isdigit()]

    @transaction.atomic
    def generer_sieges(self, nb_rangees, sieges_par_rangee, nb_pmr=2):
        """Crée un plan rectangulaire : rangées A, B, C… et sièges numérotés de 1 à n.
        Les premiers sièges de la dernière rangée sont réservés aux personnes à mobilité réduite."""
        lettres = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        sieges = []
        for i in range(nb_rangees):
            for numero in range(1, sieges_par_rangee + 1):
                pmr = i == nb_rangees - 1 and numero <= nb_pmr
                sieges.append(Siege(salle=self, rangee=lettres[i], numero=numero,
                                    type=Siege.Type.PMR if pmr else Siege.Type.STANDARD))
        Siege.objects.bulk_create(sieges)


class Siege(models.Model):
    class Type(models.TextChoices):
        STANDARD = "standard", "Standard"
        PMR = "pmr", "PMR"
        VIP = "vip", "VIP"

    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, related_name="sieges")
    rangee = models.CharField(max_length=2)
    numero = models.PositiveSmallIntegerField("numéro")
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.STANDARD)

    class Meta:
        ordering = ["salle", "rangee", "numero"]
        constraints = [models.UniqueConstraint(fields=["salle", "rangee", "numero"], name="siege_unique_par_salle")]
        verbose_name = "siège"

    def __str__(self):
        return f"{self.rangee}{self.numero}"


class Tarif(models.Model):
    """Le tarif est une donnée, pas du code : l'administrateur peut en créer sans développement."""

    libelle = models.CharField("libellé", max_length=60)
    prix = models.DecimalField(max_digits=6, decimal_places=2)
    actif = models.BooleanField(default=True)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "prix"]

    def __str__(self):
        return f"{self.libelle} ({self.prix} €)"


class SeanceQuerySet(models.QuerySet):
    def a_venir(self):
        """Séances publiées qui n'ont pas encore commencé."""
        return self.filter(statut=Seance.Statut.PUBLIEE, debut__gt=timezone.now())

    def du_jour(self, jour):
        return self.filter(debut__date=jour)


class Seance(models.Model):
    class Statut(models.TextChoices):
        PUBLIEE = "publiee", _("publiée")
        ANNULEE = "annulee", _("annulée")

    film = models.ForeignKey(Film, on_delete=models.PROTECT, related_name="seances")
    salle = models.ForeignKey(Salle, on_delete=models.PROTECT, related_name="seances")
    debut = models.DateTimeField("début")
    langue = models.CharField(max_length=30, default="français")
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.PUBLIEE)

    objects = SeanceQuerySet.as_manager()

    class Meta:
        ordering = ["debut"]
        verbose_name = "séance"
        indexes = [models.Index(fields=["debut"])]

    def __str__(self):
        local = timezone.localtime(self.debut)
        return f"{self.film} — {local:%d/%m %H:%M} — {self.salle}"

    @property
    def fin(self):
        return self.debut + timedelta(minutes=self.film.duree)

    @property
    def est_reservable(self):
        return self.statut == self.Statut.PUBLIEE and self.debut > timezone.now()

    def save(self, *args, **kwargs):
        nouvelle = self._state.adding
        with transaction.atomic():
            super().save(*args, **kwargs)
            if nouvelle:
                self.generer_places()

    def generer_places(self):
        """À la création d'une séance, une place « libre » est créée pour chaque siège de la salle
        (classe PlaceSéance du diagramme de classes)."""
        from reservation.models import PlaceSeance  # import local : évite une dépendance circulaire

        PlaceSeance.objects.bulk_create(
            [PlaceSeance(seance=self, siege=siege) for siege in self.salle.sieges.all()],
            ignore_conflicts=True,
        )
