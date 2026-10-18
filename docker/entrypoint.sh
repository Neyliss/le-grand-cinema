#!/bin/sh
# Démarrage du conteneur « web » : met la base de données à jour, puis lance la commande demandée.
set -e

python manage.py migrate --noinput

# Données de démonstration (10 salles, 3 films, comptes de test) si CHARGER_DEMO=1.
# La commande ne fait rien si des films existent déjà.
if [ "${CHARGER_DEMO:-0}" = "1" ]; then
    python manage.py charger_demo
fi

exec "$@"
