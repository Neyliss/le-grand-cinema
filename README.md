# Le Grand Cinéma — réservation en ligne (MVP)

[![Tests et Docker](https://github.com/Neyliss/le-grand-cinema/actions/workflows/ci.yml/badge.svg)](https://github.com/Neyliss/le-grand-cinema/actions/workflows/ci.yml)

Application web Django qui réalise le MVP décrit dans le dossier de conception (Bloc 1) :
programmation en ligne, plan de salle en temps réel, réservation sans compte, paiement Stripe,
billet QR par e-mail, vente au guichet sur le même stock de places, contrôle à l'entrée et pilotage.

**Guides** : [Git et GitHub](docs/guide-github.md) · [Tests](docs/guide-tests.md) · [Docker](docs/guide-docker.md)

**Schémas** (architecture AWS, cas d'utilisation, séquence et classes UML) : [docs/schemas/Le_Grand_Cinema_schemas.drawio](docs/schemas/Le_Grand_Cinema_schemas.drawio), [à ouvrir dans draw.io](https://viewer.diagrams.net/?nav=1&title=Le_Grand_Cinema_schemas.drawio#Uhttps%3A%2F%2Fraw.githubusercontent.com%2FNeyliss%2Fle-grand-cinema%2Fdevelop%2Fdocs%2Fschemas%2FLe_Grand_Cinema_schemas.drawio) sans compte.

| EPIC | Ce que fait l'application | Où regarder |
|---|---|---|
| E1 | Programmation par jour, places libres, festival, site en français et en anglais | `catalogue/` |
| E2 | Plan de salle rafraîchi toutes les 5 s, sièges bloqués 10 minutes | `reservation/` |
| E3 | Réservation (nom + e-mail), paiement Stripe Checkout, webhook signé | `reservation/`, `paiement/` |
| E4 | Billet PDF avec QR code unique, envoyé par e-mail | `billetterie/` |
| E5 | Films, salles, tarifs, séances, annulation (spectateurs remboursés et prévenus) | administration Django |
| E6 | Vente au guichet, contrôle des billets à l'entrée | `guichet/`, `billetterie/` |
| E7 | Remplissage par séance et par créneau, export CSV | `pilotage/` |

---

## 1. Installer et lancer le projet sur son ordinateur

```bash
git clone https://github.com/Neyliss/le-grand-cinema.git
cd le-grand-cinema
```

### Option A : avec Docker (le plus simple)

Avec [Docker Desktop](https://www.docker.com/products/docker-desktop/) ouvert :

```bash
docker compose up --build
```

Le site et sa base PostgreSQL démarrent ensemble, avec les données de démonstration, sur
**http://localhost:8000**. Détails et commandes utiles : [guide Docker](docs/guide-docker.md).

### Option B : avec Python

Prérequis : **Python 3.10 ou plus** (`python3 --version`) et VS Code avec l'extension Python.
Si la version est trop ancienne, installer Python depuis https://www.python.org/downloads/.

Dans le terminal de VS Code (menu *Terminal › Nouveau terminal*), à la racine du projet :

```bash
python3 -m venv .venv                 # environnement Python propre au projet
source .venv/bin/activate             # sous Windows : .venv\Scripts\activate
pip install -r requirements.txt       # installe Django, Stripe, qrcode...
cp .env.example .env                  # réglages locaux (mode développement)
python manage.py migrate              # crée la base de données SQLite
python manage.py charger_demo         # 10 salles, 3 films, 7 jours de séances, des ventes
python manage.py runserver            # lance le site
```

Puis ouvrir **http://127.0.0.1:8000**. Dans VS Code, la configuration « Django : lancer le site »
(onglet *Exécuter et déboguer*) fait la même chose avec le débogueur.

### Les espaces du site

| Adresse | Pour qui | Compte de démonstration |
|---|---|---|
| http://127.0.0.1:8000/ | Spectateurs (sans compte) | — |
| http://127.0.0.1:8000/en/ | Spectateurs, en anglais | — |
| http://127.0.0.1:8000/guichet/ | Agents d'accueil | `agent` / `agent-gc-2026` |
| http://127.0.0.1:8000/controle/ | Agents d'accueil | `agent` / `agent-gc-2026` |
| http://127.0.0.1:8000/pilotage/ | Administrateurs | `admin` / `admin-gc-2026` |
| http://127.0.0.1:8000/admin/ | Administrateurs | `admin` / `admin-gc-2026` |

Ces mots de passe servent uniquement en local. En production, on crée les comptes avec
`python manage.py createsuperuser`.

### Paiement en local

Sans clé Stripe, le site passe en **mode démonstration** : la page de paiement est simulée.
Les e-mails (billets) s'affichent dans le terminal où tourne `runserver`.

Pour tester le vrai Stripe en mode test :
1. créer un compte sur https://dashboard.stripe.com et copier la clé `sk_test_...` dans `.env` (`STRIPE_SECRET_KEY`) ;
2. installer la Stripe CLI, puis lancer `stripe listen --forward-to localhost:8000/webhooks/stripe/`
   et copier le secret `whsec_...` affiché dans `.env` (`STRIPE_WEBHOOK_SECRET`) ;
3. payer avec la carte de test `4242 4242 4242 4242`, une date future et n'importe quel code.

### Base de données : SQLite ou PostgreSQL

Par défaut, `migrate` crée le fichier `db.sqlite3` : rien à installer, pratique pour démarrer.
La production utilise **PostgreSQL** (Amazon RDS, dossier 3). Pour travailler en local avec la
même base que la production :

1. Installer **Postgres.app** (https://postgresapp.com), l'ouvrir et cliquer sur *Initialize* :
   le serveur tourne sur le port 5432.
2. Dans la fenêtre de Postgres.app, double-cliquer sur la base `postgres` : un terminal `psql`
   s'ouvre. Taper `CREATE DATABASE grandcinema;` puis `\q`.
3. Dans `.env`, écrire `DATABASE_URL=postgres://localhost:5432/grandcinema`
   (Postgres.app utilise le nom d'utilisateur du Mac, sans mot de passe). Si une fenêtre demande
   d'autoriser Python à se connecter, accepter.
4. Créer les tables et les données dans PostgreSQL :
   `python manage.py migrate` puis `python manage.py charger_demo`.

Pour revenir à SQLite, il suffit de vider `DATABASE_URL` dans `.env`. Le code ne change pas :
l'ORM de Django écrit le SQL adapté à chaque base.

## 2. Lancer les tests

```bash
python manage.py test                          # avec Python
docker compose exec web python manage.py test  # avec Docker (PostgreSQL)
```

42 tests vérifient les règles du dossier, en particulier la règle critique « un siège ne se vend
qu'une fois » (`reservation/tests/test_double_vente.py`), le blocage de 10 minutes, le parcours
complet en ligne, le webhook Stripe signé, le contrôle d'un billet déjà scanné, l'export CSV
et les données de démonstration.
Chaque module range ses tests dans un dossier `tests/`, un fichier par sujet ; GitHub les relance
à chaque envoi (onglet *Actions*). Voir le [guide des tests](docs/guide-tests.md).

Le test `ConcurrenceReelleTests` lance 5 spectateurs **en même temps** sur le même siège, avec
de vraies connexions parallèles : un seul l'obtient. Il ne tourne qu'avec PostgreSQL, car SQLite
ne sait pas verrouiller une ligne (il est alors indiqué « skipped »). Sans le verrou
`select_for_update`, ce test échoue : plusieurs spectateurs obtiennent le même siège.

## 3. Organisation du code

Le projet suit le modèle **MVT** de Django (dossier 3, figure 7) :

- `models.py` : les données (classes du diagramme de classes, figure 9) ;
- `services.py` : les règles métier, communes au site et au guichet ;
- `views.py` : reçoivent la requête, appliquent les règles, choisissent le gabarit ;
- `templates/` : les pages HTML (reprises des wireframes et mockups Figma) ;
- `static/` : feuille de style SCSS compilée en CSS, et JavaScript (plan de salle) ;
- `tests/` (dans chaque module) : les tests ; `outils_de_test/` : les données de test partagées.

Branches Git : `main` (versions stables, avec tags), `develop` (intégration) et une branche par
travail (`feature/…`, `fix/…`). Voir le [guide Git et GitHub](docs/guide-github.md).

La règle critique (dossier 3, § 3.3) se trouve dans `reservation/services.py`, fonction
`bloquer_sieges` : verrou `select_for_update` dans une transaction, plus la contrainte d'unicité
« séance + siège » de la table `PlaceSeance` (`reservation/models.py`).

Le diagramme de séquence (figure 8) se lit dans le code :
étapes 1 à 6 dans `reservation/views.py`, 7 à 11 dans `paiement/services.py`,
12 et 13 dans `billetterie/services.py` (`finaliser_billets`), 14 et 15 dans `controler_billet`.

Les sièges bloqués depuis plus de 10 minutes sont libérés automatiquement à chaque lecture du plan
et à chaque nouvelle réservation. La commande `python manage.py liberer_places` fait le même
travail pour toutes les séances ; elle peut être planifiée sur le serveur.

### Modifier le style

Le style est écrit en SCSS dans `static/scss/` et compilé dans `static/css/site.css` :

```bash
brew install sass/sass/sass           # ou : npm install -g sass
sass --watch static/scss/site.scss static/css/site.css
```

### Ajouter un texte traduit

Les textes des pages sont entourés de `{% translate "…" %}`. Après un ajout :

```bash
brew install gettext
python manage.py makemessages -l en   # ajoute le texte dans locale/en/LC_MESSAGES/django.po
# écrire la traduction anglaise dans le fichier .po, puis :
python manage.py compilemessages
```

## 4. Déployer sur AWS (dossier 3)

L'architecture retenue est un environnement **Elastic Beanstalk « instance unique »** (C3)
derrière **CloudFront** (C2), avec une base **RDS PostgreSQL** (C4), S3 (C5) et SES (C6).

1. Installer l'outil `eb` : `pip install awsebcli`.
2. `eb init` (région `eu-west-3`, plateforme Python), puis
   `eb create gc-prod --single --instance-types t4g.small`.
3. Créer la base RDS PostgreSQL `gc-prod-db` (db.t4g.micro, sous-réseau privé) et autoriser
   seulement le groupe de sécurité du serveur.
4. Dans la console Elastic Beanstalk, renseigner les propriétés de l'environnement :
   `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL`, `DATABASE_URL`,
   `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `AWS_STORAGE_BUCKET_NAME`,
   `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`.
5. `eb deploy` : les migrations et les fichiers statiques sont traités par `.ebextensions/01_django.config`.
6. Créer la distribution CloudFront devant l'environnement, transmettre l'en-tête
   `CloudFront-Forwarded-Proto` et déclarer le webhook Stripe sur `https://<domaine>/webhooks/stripe/`.

**Mode festival** : dans la console, *Configuration › Capacité*, passer le type d'environnement
de « instance unique » à « avec répartiteur de charge » (2 instances), et passer la base RDS en
Multi-AZ. Revenir au mode normal après le festival.
