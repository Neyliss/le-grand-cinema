# Guide Git et GitHub du projet

Ce guide explique comment le code du Grand Cinéma est rangé dans Git, comment s'y retrouver
sur la page GitHub du dépôt et comment travailler au quotidien depuis VS Code.

Dépôt public : **https://github.com/Neyliss/le-grand-cinema**

---

## 1. Les deux outils en une phrase

- **Git** enregistre l'historique du projet sur l'ordinateur : chaque *commit* est une photo
  des fichiers, avec un message qui dit ce qui a changé.
- **GitHub** héberge une copie de cet historique en ligne : on y lit le code, on y propose des
  modifications (*pull requests*) et les tests s'y lancent automatiquement (*Actions*).

## 2. Les branches du projet

Une **branche** est une ligne de travail parallèle. Le projet suit une organisation simple,
inspirée de « Git Flow » :

| Branche | Rôle | Règle |
|---|---|---|
| `main` | Version stable, celle qui est (ou sera) en ligne | On n'y travaille jamais directement ; elle ne reçoit que des versions testées, marquées d'un *tag* (`v1.0.0`, `v1.1.0`…) |
| `develop` | Branche d'intégration : le travail terminé s'y assemble | Reçoit les branches de travail une fois leurs tests au vert |
| `feature/…` | Une nouvelle fonctionnalité (ex. `feature/docker`) | Part de `develop`, y revient par une fusion |
| `fix/…` | Une correction de bug | Idem |
| `test/…`, `docs/…`, `ci/…` | Tests, documentation, intégration continue | Idem |

Historique actuel du dépôt :

```
main     ●─────────────────────────────────────────────────────────●  v1.1.0
         v1.0.0 (MVP)                                               ↑
develop  └──●────────────●────────────●────────────●────────────────┘
            ↑            ↑            ↑            ↑
            │            │            │            └── docs/guides
            │            │            └── ci/github-actions
            │            └── feature/docker
            └── test/organisation-des-tests
```

Chaque `●` de `develop` est une **fusion** (*merge*) d'une branche de travail. Les branches
fusionnées sont gardées pour que l'historique reste lisible.

## 3. Se repérer sur la page du dépôt

| Onglet ou zone | Ce qu'on y trouve |
|---|---|
| **Code** | Les dossiers et fichiers. Le `README.md` s'affiche en dessous : c'est la page d'accueil du projet. |
| Sélecteur de branche (bouton `main ▾` en haut à gauche) | Afficher le code d'une autre branche, par exemple `develop`. |
| **Commits** (lien avec une horloge, à droite au-dessus des fichiers) | L'historique : qui a changé quoi, quand, et pourquoi (le message). Cliquer sur un commit montre les lignes ajoutées (en vert) et retirées (en rouge). |
| **Tags** / **Releases** (colonne de droite) | Les versions publiées : `v1.0.0` (MVP), `v1.1.0`. |
| **Pull requests** | Les propositions de fusion d'une branche dans une autre, avec la discussion et le résultat des tests. |
| **Actions** | L'intégration continue : à chaque envoi, GitHub lance les tests et vérifie Docker. Une coche verte = tout passe ; une croix rouge = un problème, cliquer pour lire le détail. |
| **Insights › Network** | Le dessin des branches et des fusions. |
| **Settings** | Réglages du dépôt (nom, visibilité publique, protection des branches). |

Astuces :
- Dans un fichier, le bouton **History** montre son historique, et **Blame** indique pour chaque
  ligne le commit qui l'a écrite.
- La touche **`.`** (point) sur la page du dépôt ouvre un éditeur VS Code dans le navigateur,
  pratique pour lire le code sans rien installer.
- La touche **`t`** permet de chercher un fichier par son nom.

## 4. Récupérer le projet sur un ordinateur

Une seule fois, dans un terminal :

```bash
cd ~/Documents
git clone https://github.com/Neyliss/le-grand-cinema.git
cd le-grand-cinema
git switch develop        # on travaille toujours à partir de develop
```

Puis suivre le README (environnement Python ou Docker).

## 5. Le cycle de travail, étape par étape

Exemple : corriger le contraste des boutons.

```bash
git switch develop
git pull                                   # 1. partir de la dernière version
git switch -c fix/contraste-boutons        # 2. créer sa branche
# … modifier les fichiers …
python manage.py test                      # 3. vérifier que tout passe
git add static/scss/_base.scss static/css/site.css
git commit -m "fix(style): contraste des boutons conforme WCAG AA"   # 4. enregistrer
git push -u origin fix/contraste-boutons   # 5. envoyer la branche sur GitHub
```

6. Sur GitHub, un bandeau jaune propose **Compare & pull request** : choisir `develop` comme
   branche de destination (*base*), décrire la modification, cliquer **Create pull request**.
7. Attendre la coche verte des tests (onglet **Checks** de la pull request), puis
   **Merge pull request**.
8. Revenir sur `develop` en local : `git switch develop && git pull`.

**Publier une version** : quand `develop` est stable, ouvrir une pull request de `develop` vers
`main`, la fusionner, puis créer le tag :

```bash
git switch main && git pull
git tag -a v1.2.0 -m "Version 1.2.0"
git push origin v1.2.0
```

### Dans VS Code, sans taper de commande

- **En bas à gauche** : le nom de la branche courante. Un clic permet d'en changer ou d'en créer une.
- **Icône « Contrôle de code source »** (trois ronds reliés, à gauche) : liste des fichiers
  modifiés. Le `+` prépare un fichier (*add*), la zone de texte reçoit le message, le bouton
  **Valider** fait le *commit*.
- **Bouton « Synchroniser les modifications »** : envoie (*push*) et récupère (*pull*).
- Au premier envoi, VS Code demande de se connecter à GitHub : accepter dans le navigateur.

## 6. Écrire un bon message de commit

Format utilisé (convention *Conventional Commits*) : `type(portée): description courte`

| Type | Quand | Exemple |
|---|---|---|
| `feat` | Nouvelle fonctionnalité | `feat(guichet): impression du ticket de caisse` |
| `fix` | Correction de bug | `fix(plan): siège PMR mal affiché sur mobile` |
| `test` | Ajout ou rangement de tests | `test(paiement): cas du remboursement partiel` |
| `docs` | Documentation | `docs: guide Docker` |
| `ci` | Intégration continue | `ci: tests sur Python 3.13` |
| `refactor` | Code réorganisé sans changer le comportement | `refactor(reservation): extraire le calcul du total` |
| `chore` | Entretien (bibliothèques, configuration) | `chore: mise à jour de Django 5.2.x` |

La description dit **ce que fait** le commit, au présent, en moins de 70 caractères.
Un commit = un changement cohérent : mieux vaut trois petits commits clairs qu'un gros fourre-tout.

## 7. Bonnes pratiques à garder

- **Jamais de secret dans Git** : le fichier `.env` (clés Stripe, mots de passe) est exclu par
  `.gitignore`. Le dépôt est public : tout ce qui y entre est visible par tous, pour toujours.
- **Lancer les tests avant chaque envoi** ; GitHub les relance de toute façon.
- **Ne jamais travailler directement sur `main`.**
- **Protéger `main`** (recommandé) : *Settings › Branches › Add branch ruleset*, cocher
  « Require a pull request before merging » et « Require status checks to pass » en choisissant
  les vérifications *Tests (PostgreSQL)* et *Image Docker*. Plus personne ne peut alors casser
  `main` par erreur.
- **Garder des branches courtes** : quelques jours de travail au plus, puis fusion.

## 8. Commandes de secours

| Situation | Commande |
|---|---|
| Où en suis-je ? | `git status` |
| Voir l'historique en arbre | `git log --oneline --graph --all` |
| Annuler les modifications d'un fichier non enregistré | `git restore chemin/du/fichier` |
| Retirer un fichier préparé par erreur (`add`) | `git restore --staged chemin/du/fichier` |
| Corriger le message du dernier commit (pas encore envoyé) | `git commit --amend` |
| Mettre de côté un travail en cours pour changer de branche | `git stash`, puis `git stash pop` |
