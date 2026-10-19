# Git et GitHub : le guide simple

Le code du projet est en ligne ici : **https://github.com/Neyliss/le-grand-cinema**
(dépôt public : tout le monde peut le lire, seul son propriétaire peut le modifier).

---

## 1. Les mots à connaître

| Mot | En clair |
|---|---|
| **Git** | Un logiciel qui garde toutes les versions du code, comme un historique de sauvegardes. On peut toujours revenir en arrière. |
| **GitHub** | Le site internet où le code et son historique sont rangés en ligne. |
| **Dépôt** (*repository*) | Le dossier du projet, avec tout son historique. |
| **Commit** | Une sauvegarde, avec une phrase qui explique ce qui a changé. |
| **Branche** | Une copie de travail. On y fait une modification sans risquer de casser la version qui marche. |
| **Fusion** (*merge*) | On ramène le travail d'une branche dans une autre. |
| **Pull request** | Une demande de fusion sur GitHub. GitHub lance les tests avant qu'on accepte. |
| **Push / Pull** | *Push* : envoyer son travail sur GitHub. *Pull* : récupérer la dernière version depuis GitHub. |
| **Tag** | Une étiquette posée sur une version, par exemple `v1.0.0`. |

## 2. Les branches du projet

| Branche | À quoi elle sert |
|---|---|
| `main` | La version qui marche, prête à être mise en ligne. On n'y touche jamais directement. |
| `develop` | La branche où l'on rassemble le travail terminé et testé. |
| `feature/…` | Une nouvelle fonction. Exemple : `feature/docker`. |
| `fix/…` | Une correction. Exemple : `fix/contraste-boutons`. |
| `test/…`, `docs/…`, `ci/…` | Des tests, de la documentation, les tests automatiques de GitHub. |

Le chemin d'une modification est toujours le même :

```
branche de travail  ──►  develop  ──►  main  (nouvelle version, avec un tag)
```

## 3. Se repérer sur GitHub

Sur la page du dépôt :

- **Code** : les dossiers et les fichiers. Le `README.md` s'affiche en dessous, c'est la page
  d'accueil du projet.
- **Le bouton `main ▾`** (en haut à gauche) : choisir la branche à afficher.
- **Commits** (petite horloge au-dessus des fichiers) : la liste des sauvegardes. Un clic sur
  l'une d'elles montre ce qui a changé : en vert ce qui a été ajouté, en rouge ce qui a été retiré.
- **Pull requests** : les demandes de fusion.
- **Actions** : les tests automatiques. Une **coche verte** veut dire que tout va bien. Une
  **croix rouge** veut dire qu'un test a échoué : cliquer dessus pour voir lequel.
- **Tags** (colonne de droite) : les versions `v1.0.0`, `v1.1.0`…
- **Insights › Network** : le dessin des branches.

Deux raccourcis pratiques : la touche **`t`** cherche un fichier par son nom, la touche **`.`**
ouvre le code dans un éditeur directement dans le navigateur.

## 4. Récupérer le projet sur son ordinateur

Dans VS Code : menu **Affichage › Palette de commandes**, taper **Git: Clone**, coller
l'adresse `https://github.com/Neyliss/le-grand-cinema`, puis choisir le dossier `Documents`.

Ou dans un terminal :

```bash
cd ~/Documents
git clone https://github.com/Neyliss/le-grand-cinema.git
cd le-grand-cinema
git switch develop
```

## 5. Faire une modification, pas à pas

Exemple : corriger une faute dans une page.

**1. Partir de la dernière version de `develop`**

```bash
git switch develop
git pull
```

**2. Créer sa branche**

```bash
git switch -c fix/faute-page-infos
```

**3. Modifier les fichiers, puis vérifier que les tests passent**

```bash
python manage.py test
```

**4. Sauvegarder (commit)**

```bash
git add .
git commit -m "fix(infos): faute d'orthographe dans les tarifs"
```

**5. Envoyer la branche sur GitHub (push)**

```bash
git push -u origin fix/faute-page-infos
```

**6. Sur GitHub**, un bandeau jaune propose **Compare & pull request**. Choisir `develop` comme
destination, cliquer sur **Create pull request**, attendre la coche verte, puis cliquer sur
**Merge pull request**.

**7. Revenir sur `develop`** sur son ordinateur : `git switch develop` puis `git pull`.

### La même chose avec la souris dans VS Code

- **En bas à gauche**, le nom de la branche : cliquer dessus pour changer de branche ou en créer une.
- **L'icône « Contrôle de code source »** (trois ronds reliés, dans la barre de gauche) : la
  liste des fichiers modifiés. Écrire le message en haut, puis cliquer sur **Valider** (*commit*).
- **Le bouton « Synchroniser »** envoie et récupère les modifications.
- La première fois, VS Code demande de se connecter à GitHub : accepter.

## 6. Écrire un bon message de commit

Forme : `type(partie): ce que fait la modification`

| Type | Quand l'utiliser |
|---|---|
| `feat` | Une nouvelle fonction |
| `fix` | Une correction |
| `test` | Des tests |
| `docs` | De la documentation |
| `ci` | Les tests automatiques de GitHub |
| `refactor` | Du code réorganisé, sans changer ce qu'il fait |
| `chore` | De l'entretien (mise à jour d'une bibliothèque…) |

Exemple : `feat(guichet): impression du ticket de caisse`. La phrase est courte, au présent, et
dit **ce que fait** la modification.

## 7. Les règles d'or

1. **Jamais de mot de passe ni de clé secrète dans Git.** Le fichier `.env` est exclu
   automatiquement. Le dépôt est public : ce qui y entre est visible par tous.
2. **On ne travaille jamais directement sur `main`.**
3. **On lance les tests avant d'envoyer.** GitHub les relance de toute façon.
4. **Petites modifications, petits commits** : c'est plus facile à relire et à annuler.
5. **Protéger `main`** (conseillé) : dans **Settings › Branches**, ajouter une règle qui oblige
   à passer par une pull request avec les tests au vert.

## 8. En cas de doute

| Je veux… | Commande |
|---|---|
| Savoir où j'en suis | `git status` |
| Voir l'historique | `git log --oneline --graph --all` |
| Annuler mes changements sur un fichier | `git restore chemin/du/fichier` |
| Mettre mon travail de côté pour changer de branche | `git stash` (et `git stash pop` pour le reprendre) |
