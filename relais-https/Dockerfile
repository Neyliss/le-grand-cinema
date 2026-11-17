# Relais HTTPS provisoire devant le serveur Elastic Beanstalk (remplace CloudFront, composant C2,
# tant qu'AWS n'a pas validé le compte pour CloudFront). Guide : docs/guide-relais-https.md
# Image nginx officielle « sans droits d'administrateur » (l'utilisateur nginx, pas root).
FROM nginxinc/nginx-unprivileged:1.27-alpine

# Le modèle est complété au démarrage avec les variables PORT (donnée par Render) et ORIGINE
# (adresse du serveur Elastic Beanstalk, sans http://).
COPY default.conf.template /etc/nginx/templates/default.conf.template
