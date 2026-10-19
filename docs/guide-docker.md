# Docker : le guide simple

**Docker** permet de lancer le site et sa base de données avec **une seule commande**, sans
installer Python ni PostgreSQL sur son ordinateur. Tout le monde a ainsi exactement le même
environnement, proche de celui de la mise en ligne.

---

## 1. Les mots à connaître

| Mot | En clair |
|---|---|
| **Image** | Une boîte toute prête qui contient le système, Python, les bibliothèques et le code du site. |
| **Conteneur** | Une image qui tourne. Il est isolé du reste de l'ordinateur. |
| **Docker Compose** | Lance plusieurs conteneurs qui travaillent ensemble. Ici : le site et la base de données. |

Le projet utilise deux conteneurs :

- **`web`** : le site Django ;
- **`db`** : la base de données PostgreSQL.

## 2. Installer Docker (une seule fois)

1. Télécharger **Docker Desktop** : https://www.docker.com/products/docker-desktop/
   (choisir la version pour Mac avec puce Apple ou puce Intel).
2. L'installer et l'ouvrir. Une petite baleine apparaît en haut de l'écran.
3. Vérifier dans le terminal : `docker --version`

Docker Desktop doit être **ouvert** pour que les commandes fonctionnent.

## 3. Lancer le site

Dans le terminal, dans le dossier du projet :

```bash
docker compose up --build
```

La première fois, Docker télécharge ce qu'il faut : cela prend quelques minutes. Les fois
suivantes, quelques secondes suffisent.

Ouvrir ensuite **http://localhost:8000**. Les données de démonstration sont déjà là, avec les
comptes `admin` / `admin-gc-2026` et `agent` / `agent-gc-2026`.

## 4. Les commandes du quotidien

| Je veux… | Commande |
|---|---|
| Lancer le site | `docker compose up` |
| Le lancer en gardant le terminal libre | `docker compose up -d` |
| Arrêter le site | `Ctrl + C`, puis `docker compose down` |
| Voir les messages du site | `docker compose logs -f web` |
| Lancer les tests | `docker compose exec web python manage.py test` |
| Créer un compte administrateur | `docker compose exec web python manage.py createsuperuser` |
| Repartir avec une base vide | `docker compose down -v`, puis `docker compose up` |
| Reconstruire après un ajout dans `requirements.txt` | `docker compose up --build` |

Bon à savoir : le code de l'ordinateur est **partagé** avec le conteneur. Quand on modifie un
fichier, le site le prend en compte tout de suite, sans rien relancer.

## 5. Les fichiers Docker du projet

| Fichier | Ce qu'il fait |
|---|---|
| `Dockerfile` | La recette de l'image : Python, les bibliothèques, puis le code du site. |
| `docker-compose.yml` | Décrit les deux conteneurs (`web` et `db`) et comment ils se parlent. |
| `docker/entrypoint.sh` | Ce qui se passe au démarrage : création des tables, puis données de démonstration. |
| `.dockerignore` | Ce qui ne doit jamais entrer dans l'image, comme le fichier `.env` qui contient les secrets. |

## 6. Docker et la mise en ligne

- Avec `docker compose up`, le site tourne en **mode développement** (messages d'erreur détaillés).
- L'image peut aussi tourner en **mode production**, avec le serveur Gunicorn. GitHub vérifie
  automatiquement que ce mode fonctionne à chaque envoi.
- Les mots de passe et les clés ne sont **jamais** dans l'image : on les donne au moment du
  lancement.
- Aujourd'hui, la mise en ligne sur AWS se fait sans Docker (voir le README). Mais la même image
  pourrait être utilisée plus tard sur AWS, sans changer le code.

## 7. Si quelque chose ne marche pas

| Problème | Solution |
|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop n'est pas ouvert : l'ouvrir et attendre que la baleine ne bouge plus. |
| `port is already allocated` | Le port 8000 est déjà pris, souvent par un `python manage.py runserver` lancé à côté. L'arrêter, puis relancer. |
| Une bibliothèque est introuvable | Reconstruire : `docker compose up --build`. |
| Les données sont bizarres | Repartir de zéro : `docker compose down -v`, puis `docker compose up`. |
