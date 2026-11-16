#!/bin/sh
# Démarrage du conteneur « web » : met la base de données à jour, puis lance la commande demandée.
set -e

python manage.py migrate --noinput

# Données de démonstration (10 salles, 3 films, comptes de test) si CHARGER_DEMO=1.
# --si-perime : rien n'est rechargé tant que la programmation couvre encore 3 jours ; sinon tout
# est rechargé pour les 7 jours suivants (le site de démonstration reste à jour sans tâche planifiée).
if [ "${CHARGER_DEMO:-0}" = "1" ]; then
    python manage.py charger_demo --si-perime
fi

exec "$@"
