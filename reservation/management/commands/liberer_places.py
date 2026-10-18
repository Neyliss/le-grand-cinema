"""Tâche planifiée : remet « libres » les sièges dont le blocage de 10 minutes est dépassé.
Lancée chaque minute sur le serveur (voir .ebextensions/02_taches.config)."""
from django.core.management.base import BaseCommand

from reservation.services import liberer_places_expirees


class Command(BaseCommand):
    help = "Libère les sièges bloqués depuis plus de 10 minutes sans paiement."

    def handle(self, *args, **options):
        nb = liberer_places_expirees()
        self.stdout.write(f"{nb} place(s) libérée(s).")
