# Mettre le site en ligne sur AWS : le guide pas à pas

Ce guide met en ligne le **site de démonstration** (recette) : le vrai code, avec des données
d'exemple et un paiement simulé. Tout se fait dans la **console AWS**, avec la souris, sans
outil à installer. Compter **45 minutes** la première fois (dont 15 minutes d'attente).

```
Spectateur ──HTTPS──► CloudFront ──HTTP──► Elastic Beanstalk (Django) ──► RDS PostgreSQL
                      (adresse publique)    1 serveur t3.micro             base de données
```

| Service | Rôle | Dans le bloc 1 |
|---|---|---|
| **Elastic Beanstalk** | installe et fait tourner le site sur un serveur | C3 |
| **RDS PostgreSQL** | la base de données | C4 |
| **CloudFront** | l'adresse publique en HTTPS (cadenas du navigateur) | C2 |

**Coût** : environ 25 $ par mois (serveur, base, adresse IP), **pris sur les crédits de l'offre
gratuite** (100 à 200 $ pendant 6 mois). Rien n'est facturé tant que le compte reste sur l'offre
gratuite. Pensez à tout supprimer après l'examen (étape 8).

---

## Étape 0 : avant de commencer

1. Se connecter à la console AWS et choisir la région **Europe (Paris) eu-west-3** (en haut à droite).
2. **Alerte de budget** (5 minutes, et 20 $ de crédits en plus) : rechercher **Budgets** >
   *Créer un budget* > modèle **Budget à dépense nulle** > saisir son e-mail > *Créer*.
   AWS prévient par e-mail dès le premier centime dépensé.
3. Avoir le fichier **`le-grand-cinema.zip`** (le code de la version `v2.0.0`). Il est créé par le
   script de publication. Sinon, dans le dossier du projet :
   `git archive --format=zip -o le-grand-cinema.zip main`
4. Créer une **clé secrète** Django (une longue suite de caractères au hasard) dans le Terminal :
   `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`. La garder pour l'étape 3.
5. Choisir le **mot de passe des comptes du personnel** (`admin` et `agent`) du site en ligne :
   au moins 12 caractères, utilisé nulle part ailleurs. Le garder pour l'étape 3 : c'est lui qu'on
   donne au jury. Les mots de passe du README ne marchent qu'en local.

## Étape 1 : le rôle du serveur (une seule fois)

Le serveur a besoin d'une autorisation pour fonctionner avec Elastic Beanstalk.

1. Rechercher **IAM** > *Rôles* > *Créer un rôle*.
2. Entité de confiance : **Service AWS**, cas d'utilisation : **EC2** > *Suivant*.
3. Cocher les autorisations **AWSElasticBeanstalkWebTier** > *Suivant*.
4. Nom du rôle : **aws-elasticbeanstalk-ec2-role** > *Créer le rôle*.

## Étape 2 : créer l'application Elastic Beanstalk

Rechercher **Elastic Beanstalk** > *Créer une application*.

| Écran | Réglage | Valeur |
|---|---|---|
| Configurer l'environnement | Niveau | **Environnement de serveur web** |
| | Nom de l'application | `le-grand-cinema` |
| | Nom de l'environnement | `gc-prod` |
| | Plateforme | **Python**, branche **Python 3.12 running on 64bit Amazon Linux 2023** |
| | Code de l'application | **Charger votre code** > fichier `le-grand-cinema.zip`, étiquette `v2.0.0` |
| | Préréglages | **Instance unique (éligible à l'offre gratuite)** |
| Accès au service | Rôle de service | **Créer et utiliser un nouveau rôle de service** |
| | Profil d'instance EC2 | `aws-elasticbeanstalk-ec2-role` (étape 1) |
| | Paire de clés EC2 | laisser vide |
| Réseau et base de données | VPC | celui par défaut ; cocher **Adresse IP publique** et tous les sous-réseaux |
| | Base de données | **Activer** |
| | Moteur | **postgres** (dernière version proposée) |
| | Classe d'instance | **db.t4g.micro** (ou db.t3.micro) |
| | Stockage | **20** Go |
| | Nom d'utilisateur, mot de passe | à choisir ; ne les écrire nulle part dans le code |
| | Conservation de la base | **Supprimer** (pas de copie payante à la fin) |
| Instances et mise à l'échelle | Types d'instance | garder **t3.micro** seulement |
| Mises à jour et surveillance | Propriétés de l'environnement | voir l'étape 3 |

## Étape 3 : les propriétés de l'environnement

Toujours dans l'assistant, écran *Mises à jour, surveillance et journalisation*, en bas :
**Propriétés de l'environnement** > *Ajouter une propriété*.

| Nom | Valeur | À quoi ça sert |
|---|---|---|
| `SECRET_KEY` | la clé créée à l'étape 0 | signer les sessions et les liens ; le site refuse de démarrer sans elle |
| `ALLOWED_HOSTS` | `.elasticbeanstalk.com,.cloudfront.net` | adresses par lesquelles le site accepte d'être appelé |
| `MOT_DE_PASSE_DEMO` | le mot de passe choisi à l'étape 0 | mot de passe des comptes `admin` et `agent` ; sans lui, ces comptes sont bloqués |

Les autres réglages sont déjà dans le code (`.ebextensions/01_django.config`) : `DEBUG=False`,
paiement simulé, dossier des affiches. Les accès à la base (`RDS_HOSTNAME`, `RDS_PASSWORD`…)
sont donnés par AWS lui-même.

Cliquer sur **Soumettre**. AWS crée la base et le serveur : **10 à 15 minutes**. À la fin, la
santé de l'environnement passe au **vert (Ok)** et une adresse s'affiche, par exemple
`gc-prod.eu-west-3.elasticbeanstalk.com`.

**Ce qui se passe au déploiement**, tout seul : installation des bibliothèques
(`requirements.txt`), mise à jour de la base (`migrate`), fichiers de style (`collectstatic`),
chargement de la démonstration (`charger_demo` : 10 salles, 3 films, 7 jours de séances,
comptes de test), puis démarrage du site avec Gunicorn (`Procfile`). Deux tâches planifiées
sont installées : libérer les sièges non payés chaque minute, et recharger la démonstration
chaque nuit.

## Étape 4 : l'adresse publique en HTTPS (CloudFront)

Le serveur répond seulement en HTTP. Pour le **cadenas** (HTTPS), on place CloudFront devant,
comme prévu au bloc 1. Sans cette étape, la connexion aux comptes ne marche pas : c'est voulu,
les mots de passe ne doivent jamais passer en clair.

Rechercher **CloudFront** > *Créer une distribution*. Si l'assistant propose un **plan
tarifaire**, choisir le plan **gratuit (Free)**.

| Réglage | Valeur |
|---|---|
| Origine (domaine) | l'adresse Elastic Beanstalk de l'étape 3 (`gc-prod….elasticbeanstalk.com`) |
| Protocole vers l'origine | **HTTP uniquement** |
| Politique de protocole des spectateurs | **Rediriger HTTP vers HTTPS** |
| Méthodes HTTP autorisées | **GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE** |
| Politique de cache | **CachingDisabled** (chaque page est à jour : plan de salle en temps réel) |
| Politique de requête d'origine | **AllViewerAndCloudFrontHeaders-2022-06** |
| Pare-feu (WAF) | **Ne pas activer** (payant) |

Cliquer sur *Créer*. Après **5 minutes**, la distribution est déployée et affiche son adresse,
par exemple `d1abcdef.cloudfront.net`.

## Étape 5 : donner l'adresse publique au site

Elastic Beanstalk > `gc-prod` > *Configuration* > *Mises à jour, surveillance et journalisation*
> *Modifier* > Propriétés de l'environnement, ajouter :

| Nom | Valeur |
|---|---|
| `SITE_URL` | `https://d1abcdef.cloudfront.net` (l'adresse CloudFront) |

*Appliquer*. Le site redémarre (1 minute). Désormais, une visite de l'adresse
`…elasticbeanstalk.com` est renvoyée vers l'adresse CloudFront en HTTPS.

## Étape 6 : vérifier

Ouvrir **`https://d1abcdef.cloudfront.net`** :

| Je vérifie | Où | Compte |
|---|---|---|
| La programmation s'affiche, en français et en anglais | `/` et `/en/` | aucun |
| Réserver et payer (paiement simulé), recevoir le billet QR | une séance | aucun |
| Mon compte, ma carte d'abonnement | *Se connecter* | `spectateur.demo@exemple.fr` / `spectateur-gc-2026` |
| Le guichet et le contrôle des billets | `/guichet/`, `/controle/` | `agent` / mot de passe `MOT_DE_PASSE_DEMO` |
| Le pilotage et l'administration | `/pilotage/`, `/admin/` | `admin` / mot de passe `MOT_DE_PASSE_DEMO` |
| La documentation de l'API | `/api/docs/` | aucun |

Les e-mails (billets, confirmation de compte) ne partent pas vraiment sur ce site de
démonstration : ils sont écrits dans le journal (*Journaux* > *Demander les journaux*), et le
lien de confirmation du compte s'affiche directement à l'écran.

## Étape 7 : mettre à jour le site

Après une nouvelle version : créer le zip (étape 0), puis Elastic Beanstalk > `gc-prod` >
**Charger et déployer**. Le site est mis à jour en 2 à 3 minutes ; la base est conservée.

## Étape 8 : tout arrêter après l'examen

1. CloudFront : sélectionner la distribution > *Désactiver*, attendre, puis *Supprimer*.
2. Elastic Beanstalk : `gc-prod` > *Actions* > **Terminer l'environnement** (supprime aussi le
   serveur et la base).
3. Vérifier dans **RDS** et **EC2** qu'il ne reste rien, et dans **Billing** que les crédits ne
   baissent plus.

## En cas de problème

| Ce que je vois | Ce que je fais |
|---|---|
| Santé **rouge** après le déploiement | *Journaux* > *Demander les journaux* > *100 dernières lignes* : l'erreur est écrite en clair |
| « Bad Request (400) » | vérifier `ALLOWED_HOSTS` (étape 3) |
| La connexion ne marche pas | utiliser l'adresse **CloudFront** en `https://`, pas celle d'Elastic Beanstalk ; vérifier `SITE_URL` |
| `admin` ou `agent` refusé | vérifier `MOT_DE_PASSE_DEMO` (étape 3), puis redéployer la même version (*Charger et déployer*) ; après 10 essais faux, attendre 15 minutes |
| « CSRF » au moment d'envoyer un formulaire | vérifier la politique de requête d'origine de CloudFront (étape 4) et `SITE_URL` |
| Aucune séance visible | la démonstration se recharge chaque nuit ; pour le faire tout de suite, redéployer la même version (*Charger et déployer*) : elle est rechargée si la programmation est périmée |

**Plus tard, en vrai production** (bloc 1) : vraie clé Stripe (`STRIPE_SECRET_KEY`,
`STRIPE_WEBHOOK_SECRET`) et `PAIEMENT_DEMO=False`, e-mails par Amazon SES, affiches et billets
dans S3 (`AWS_STORAGE_BUCKET_NAME`), deux serveurs avec répartiteur de charge pendant le festival.
