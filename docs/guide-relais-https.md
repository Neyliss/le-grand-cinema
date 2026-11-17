# Relais HTTPS provisoire sur Render (en attendant CloudFront)

Ce guide sert quand le site tourne déjà sur AWS (Elastic Beanstalk et RDS, [guide AWS](guide-aws.md)
étapes 0 à 3) mais qu'AWS n'a pas encore validé le compte pour **CloudFront**. Sans CloudFront, le
site n'est joignable qu'en HTTP : les pages s'affichent, mais les connexions sont refusées (le site
n'envoie pas de mot de passe sans HTTPS).

Le relais remplace **seulement CloudFront** (composant C2), le temps de la validation :

```
Visiteur ──HTTPS──▶ Relais Render (nginx) ──HTTP──▶ Elastic Beanstalk (C3) ──▶ RDS PostgreSQL (C4)
                    remplace CloudFront (C2)         reste sur AWS                reste sur AWS
```

Le relais fait exactement ce que ferait CloudFront : il reçoit les visiteurs en HTTPS et transmet
tout au serveur Elastic Beanstalk, avec le même en-tête `CloudFront-Forwarded-Proto`. Le code du
site ne change pas. Le relais est un simple nginx (dossier [`relais-https/`](../relais-https)) :
il ne garde aucune donnée.

**Limite de l'offre gratuite** : après 15 minutes sans visite, Render met le relais en veille ; la
visite suivante le réveille en **1 minute environ**.

Durée : **15 minutes**. Gratuit, sans carte bancaire.

## Étape 1 : créer le relais chez Render

1. Aller sur **https://render.com** > *Get Started* > **GitHub**, et autoriser Render à lire le
   dépôt `le-grand-cinema`.
2. **New** > **Web Service** > choisir le dépôt `le-grand-cinema`.

| Réglage | Valeur |
|---|---|
| Name | `le-grand-cinema-https` |
| Language | **Docker** |
| Branch | `main` |
| Region | **Frankfurt (EU Central)** |
| Root Directory | **`relais-https`** |
| Instance Type | **Free** |

3. *Environment Variables* > une seule variable :

| Nom | Valeur |
|---|---|
| `ORIGINE` | l'adresse de l'environnement Elastic Beanstalk, **sans** `http://` ni `/` à la fin (exemple : `le-grand-cinema-env.eba-abcd1234.eu-west-3.elasticbeanstalk.com`) |

4. **Deploy Web Service** : 2 à 3 minutes. L'adresse du relais s'affiche en haut, par exemple
   **`https://le-grand-cinema-https.onrender.com`**.

## Étape 2 : donner cette adresse au site (Elastic Beanstalk)

Elastic Beanstalk > l'environnement > *Configuration* > **Détails de l'environnement** > *Modifier* >
Propriétés de l'environnement :

| Nom | Valeur |
|---|---|
| `ALLOWED_HOSTS` | `.elasticbeanstalk.com,.cloudfront.net,.onrender.com` |
| `SITE_URL` | l'adresse du relais, par exemple `https://le-grand-cinema-https.onrender.com` |

Supprimer `HTTPS_OBLIGATOIRE` si elle a été ajoutée pour un essai. *Appliquer* : 1 minute.
Désormais, une visite sur l'adresse Elastic Beanstalk est renvoyée vers l'adresse HTTPS du relais.

## Étape 3 : vérifier

Sur l'adresse du relais, de préférence depuis un téléphone en 4G : les mêmes vérifications que
l'étape 6 du [guide AWS](guide-aws.md) (programmation, réservation, connexions spectateur, agent et
admin, documentation de l'API).

## Quand AWS valide CloudFront

1. Créer la distribution CloudFront ([guide AWS](guide-aws.md), étape 4).
2. Mettre son adresse dans `SITE_URL` (étape 5).
3. Supprimer le relais : Render > le service > *Settings* > **Delete Web Service**.

## En cas de problème

| Ce que je vois | Ce que je fais |
|---|---|
| La page met 1 minute à s'ouvrir | normal après 15 minutes sans visite (veille gratuite) |
| *502 Bad Gateway* | vérifier `ORIGINE` (adresse exacte, sans `http://`) et que l'environnement est vert ; si l'environnement a été reconstruit, relancer le relais (*Manual Deploy*) |
| *Bad Request (400)* | ajouter `.onrender.com` dans `ALLOWED_HOSTS` (étape 2) |
| Connexion refusée, page qui revient au formulaire | vérifier `SITE_URL` : l'adresse exacte du relais, en `https://` |
