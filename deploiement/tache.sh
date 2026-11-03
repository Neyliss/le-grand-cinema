#!/bin/bash
# Lance une commande Django sur le serveur Elastic Beanstalk, avec les mêmes réglages que le site.
# Utilisé par les tâches planifiées (.ebextensions/02_taches.config). Exemple :
#   /bin/bash /var/app/current/deploiement/tache.sh liberer_places
set -euo pipefail
cd /var/app/current
PYTHON=$(ls -d /var/app/venv/*/bin/python | head -n 1)

# Réglages du site (clé secrète, base de données…) lus dans la configuration Elastic Beanstalk
eval "$(/opt/elasticbeanstalk/bin/get-config environment | "$PYTHON" -c '
import json, shlex, sys
for cle, valeur in json.load(sys.stdin).items():
    print(f"export {cle}={shlex.quote(str(valeur))}")
')"

# La commande tourne avec l'utilisateur du site (webapp), jamais en administrateur
exec runuser -u webapp -- "$PYTHON" manage.py "$@"
