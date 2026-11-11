# Mettre le site en ligne sur Render (sans AWS)

Ce guide sert quand AWS n'est pas disponible (par exemple un compte AWS encore en cours de
vérification). Le site tourne alors sur **Render** et sa base **PostgreSQL** chez **Neon**, deux
services gratuits, sans carte bancaire, avec une connexion par le compte GitHub.

**Ce qui ne change pas** : le code, l'image Docker (`Dockerfile`), la base PostgreSQL, le HTTPS
et les réglages de sécurité. L'architecture cible reste celle d'AWS ([guide AWS](guide-aws.md)).

| | AWS (cible du bloc 1) | Render + Neon (solution de secours) |
|---|---|---|
| Serveur | Elastic Beanstalk (C3) | Render, service web Docker |
| HTTPS | CloudFront (C2) | fourni par Render |
| Base | RDS PostgreSQL (C4) | Neon PostgreSQL |
| Démonstration à jour | tâche planifiée chaque nuit | rechargée au démarrage du site quand elle périme |

**Limites de l'offre gratuite** :
- après 15 minutes sans visite, Render met le site en veille. La visite suivante le réveille en
  **environ 1 minute** : c'est normal ;
- le disque du serveur est effacé à chaque redémarrage. Les données sont dans la base Neon, donc
  rien n'est perdu ; les affiches de la démonstration sont remises au démarrage.

Durée totale : **20 minutes environ**.

## Étape 0 : avant de commencer

1. Avoir un compte **GitHub** avec le dépôt `le-grand-cinema` (branche `main` à jour).
2. Choisir le **mot de passe des comptes du personnel** (`admin` et `agent`) : au moins
   12 caractères, utilisé nulle part ailleurs. C'est lui qu'on donne au jury.

## Étape 1 : la base PostgreSQL chez Neon

1. Aller sur **https://neon.com** > *Sign up* > **Continue with GitHub**.
2. Créer un projet :

| Réglage | Valeur |
|---|---|
| Nom du projet | `le-grand-cinema` |
| Version de Postgres | la version proposée par défaut |
| Fournisseur et région | **AWS**, **Europe Central 1 (Frankfurt)** |

3. Sur le tableau de bord du projet, cliquer sur **Connect**. Dans la fenêtre :
   - **Connection pooling** : **désactivé** ;
   - copier la ligne qui commence par `postgresql://…` (bouton *Copy snippet*). C'est l'adresse
     de la base, avec son mot de passe : la garder pour l'étape 2, sans la publier nulle part.

## Étape 2 : le site chez Render

1. Aller sur **https://render.com** > *Get Started* > **GitHub**. Autoriser Render à lire le
   dépôt `le-grand-cinema` (ou tous les dépôts).
2. En haut : **New** > **Blueprint**. Choisir le dépôt `le-grand-cinema`. Render lit le fichier
   [`render.yaml`](../render.yaml) : tous les réglages y sont déjà (Docker, offre gratuite,
   région Francfort, paiement simulé, démonstration, clé secrète créée par Render).
3. **Nom du Blueprint** : `le-grand-cinema`. Render demande deux valeurs :

| Nom | Valeur |
|---|---|
| `DATABASE_URL` | l'adresse Neon copiée à l'étape 1 (`postgresql://…`) |
| `MOT_DE_PASSE_DEMO` | le mot de passe choisi à l'étape 0 |

4. Cliquer sur **Deploy Blueprint** (ou *Apply*). Render construit l'image Docker puis démarre le
   site : **5 à 10 minutes**. Au démarrage, le site crée les tables (`migrate`) et charge la
   démonstration (`charger_demo` : 10 salles, 3 films, 7 jours de séances).
5. Quand l'état passe à **Live**, l'adresse s'affiche en haut de la page du service, par exemple
   **`https://le-grand-cinema.onrender.com`**. Le site connaît lui-même cette adresse : rien
   d'autre à régler.

## Étape 3 : vérifier

Ouvrir l'adresse du site (de préférence sur un téléphone en 4G) :

| Je vérifie | Où | Compte |
|---|---|---|
| La programmation s'affiche, en français et en anglais | `/` et `/en/` | aucun |
| Réserver et payer (paiement simulé), recevoir le billet QR | une séance | aucun |
| Mon compte, ma carte d'abonnement | *Se connecter* | `spectateur.demo@exemple.fr` / `spectateur-gc-2026` |
| Le guichet et le contrôle des billets | `/guichet/`, `/controle/` | `agent` / mot de passe `MOT_DE_PASSE_DEMO` |
| Le pilotage et l'administration | `/pilotage/`, `/admin/` | `admin` / mot de passe `MOT_DE_PASSE_DEMO` |
| La documentation de l'API | `/api/docs/` | aucun |

Les messages du serveur se lisent dans Render > le service > **Logs**.

## Étape 4 : mettre à jour le site

Chaque fusion sur `main` est mise en ligne toute seule par Render (5 à 10 minutes). Pour
relancer à la main : le service > **Manual Deploy** > *Deploy latest commit*.

## Étape 5 : tout arrêter après l'examen

1. Render : le service > *Settings* > **Delete Web Service** ; puis *Blueprints* > supprimer le
   Blueprint.
2. Neon : le projet > *Settings* > **Delete project**.

## En cas de problème

| Ce que je vois | Ce que je fais |
|---|---|
| La page met 1 minute à s'ouvrir | normal après 15 minutes sans visite (mise en veille gratuite) |
| *Deploy failed* | Render > le service > **Logs** : lire la dernière erreur |
| `could not connect to server` ou `password authentication failed` dans les logs | vérifier `DATABASE_URL` (Render > le service > *Environment*) : la ligne Neon complète, sans espace |
| `admin` ou `agent` refusé | vérifier `MOT_DE_PASSE_DEMO`, puis *Manual Deploy* ; après 10 essais faux, attendre 15 minutes |
| *Bad Request (400)* | l'adresse utilisée n'est pas celle affichée par Render |
