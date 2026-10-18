# Guide Docker du projet

Docker lance le site **et** sa base PostgreSQL avec une seule commande, sans rien installer
d'autre que Docker. Tout le monde travaille ainsi dans le même environnement, proche de la
production.

---

## 1. Docker en trois mots

| Mot | Définition | Dans le projet |
|---|---|---|
| **Image** | Un modèle figé : système, Python, bibliothèques et code | Construite à partir du `Dockerfile` |
| **Conteneur** | Une image en marche, isolée du reste de l'ordinateur | `web` (le site Django) et `db` (PostgreSQL) |
| **Docker Compose** | Lance plusieurs conteneurs qui travaillent ensemble | Décrit dans `docker-compose.yml` |

## 2. Installer Docker (une seule fois)

1. Télécharger **Docker Desktop** sur https://www.docker.com/products/docker-desktop/
   (choisir « Mac with Apple chip » ou « Mac with Intel chip » selon le Mac).
2. L'installer, puis l'ouvrir : la baleine apparaît dans la barre des menus.
3. Vérifier dans un terminal : `docker --version` puis `docker compose version`.

Docker Desktop doit être ouvert chaque fois qu'on utilise les commandes ci-dessous.

## 3. Lancer le projet

À la racine du projet :

```bash
docker compose up --build
```

La première fois, Docker télécharge Python et PostgreSQL et installe les bibliothèques
(quelques minutes). Ensuite, le démarrage prend quelques secondes. Au démarrage, le conteneur
crée les tables et charge les données de démonstration.

Le site répond sur **http://localhost:8000**, avec les comptes du README
(`admin` / `admin-gc-2026`, `agent` / `agent-gc-2026`).

| Pour… | Commande |
|---|---|
| Arrêter | `Ctrl + C` dans le terminal, puis `docker compose down` |
| Lancer en arrière-plan (le terminal reste libre) | `docker compose up -d` |
| Voir les messages du site | `docker compose logs -f web` |
| Repartir d'une base vide | `docker compose down -v` (efface les données PostgreSQL), puis `docker compose up` |
| Reconstruire après une modification de `requirements.txt` | `docker compose up --build` |

Le code du dossier est **partagé** avec le conteneur : une modification d'un fichier Python ou
d'un gabarit est prise en compte tout de suite, sans reconstruire.

## 4. Commandes utiles pendant le développement

Le site doit tourner (`docker compose up -d`). `exec web` exécute une commande dans le
conteneur du site :

| Pour… | Commande |
|---|---|
| Lancer les tests (sur PostgreSQL : les 35 tournent) | `docker compose exec web python manage.py test` |
| Créer un compte administrateur | `docker compose exec web python manage.py createsuperuser` |
| Appliquer de nouvelles migrations | `docker compose exec web python manage.py migrate` |
| Ouvrir la console Django | `docker compose exec web python manage.py shell` |
| Ouvrir la base en SQL | `docker compose exec db psql -U cinema grandcinema` |
| Recharger les données de démonstration | `docker compose exec web python manage.py charger_demo --reinitialiser` |
| Voir les conteneurs en marche | `docker compose ps` |

## 5. Ce que contient chaque fichier

| Fichier | Rôle |
|---|---|
| `Dockerfile` | Recette de l'image : Python 3.12, bibliothèques de `requirements.txt`, code, fichiers statiques rassemblés, utilisateur sans droits d'administrateur, démarrage avec Gunicorn. |
| `docker-compose.yml` | Les deux services : `db` (PostgreSQL 16, données gardées dans un volume) et `web` (le site, en mode développement sur le port 8000). `web` attend que la base soit prête. |
| `docker/entrypoint.sh` | Script lancé au démarrage du conteneur : migrations, puis données de démonstration si `CHARGER_DEMO=1`. |
| `.dockerignore` | Ce qui n'entre jamais dans l'image : `.env` (secrets), `.git`, base SQLite locale, fichiers temporaires. |

L'ordre des étapes du `Dockerfile` n'est pas un hasard : les bibliothèques sont installées
**avant** de copier le code. Tant que `requirements.txt` ne change pas, Docker réutilise cette
étape déjà prête et la reconstruction ne prend que quelques secondes.

## 6. Docker et la production

- En développement, `docker-compose.yml` lance `runserver` avec `DEBUG=True`.
- Sans commande particulière, l'image lance **Gunicorn**, le serveur de production, avec
  `DEBUG=False`. L'intégration continue vérifie à chaque envoi sur GitHub que cette image démarre
  et sert les pages.
- Les secrets (`SECRET_KEY`, clés Stripe, mot de passe de la base) ne sont **jamais** dans
  l'image : on les donne au démarrage, par des variables d'environnement.
- Aujourd'hui, la production tourne sur la plateforme Python d'Elastic Beanstalk (voir le
  README). La même image pourrait être déployée sur la plateforme Docker d'Elastic Beanstalk ou
  sur Amazon ECS, sans changer le code.

## 7. Problèmes fréquents

| Message ou symptôme | Cause et solution |
|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop n'est pas ouvert : l'ouvrir et attendre la baleine fixe. |
| `port is already allocated` (8000) | Un autre serveur utilise le port, souvent `python manage.py runserver` lancé à côté : l'arrêter, ou remplacer `"8000:8000"` par `"8001:8000"` dans `docker-compose.yml`. |
| Une bibliothèque ajoutée est introuvable | Reconstruire : `docker compose up --build`. |
| Les données sont dans un état bizarre | Repartir de zéro : `docker compose down -v` puis `docker compose up`. |
| Le site affiche une erreur de base de données au tout premier lancement | PostgreSQL démarrait encore : relancer `docker compose up`. |
