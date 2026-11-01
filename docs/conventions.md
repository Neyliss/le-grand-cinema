# Conventions du projet : branches, commits et merge requests

Ces règles disent **comment nommer** chaque branche et chaque commit, et **par où passe** une
modification avant d'arriver en production. Elles valent pour tout le projet.

## 1. Les deux branches permanentes

| Branche | Rôle | Qui écrit dedans |
|---|---|---|
| `main` | La version en ligne. Chaque version porte une étiquette (`v1.0.0`, `v2.0.0`…). | Uniquement par une merge request venant de `develop` |
| `develop` | Le travail terminé et testé, qui attend la prochaine version. | Uniquement par des merge requests venant des branches de travail |

On ne travaille **jamais** directement sur `main` ni sur `develop`.

## 2. Les branches de travail

Forme : **`type/sujet-en-minuscules`**, sans accent ni espace, avec des tirets.

| Type | Quand | Exemple |
|---|---|---|
| `feature/` | Une user story ou une nouvelle fonction | `feature/e3-us1-reserver-sans-compte` |
| `fix/` | La correction d'un bug | `fix/paiement-seance-annulee` |
| `test/` | Des tests seuls | `test/organisation-des-tests` |
| `docs/` | De la documentation | `docs/conventions-branches` |
| `ci/` | Les contrôles automatiques (GitHub Actions, SonarCloud) | `ci/sonarcloud` |

**Pour une user story**, le sujet commence par son identifiant du tableau Trello, puis quelques
mots : `feature/e<numéro d'EPIC>-us<numéro>-<titre-court>`. On retrouve ainsi tout de suite la
carte Trello qui correspond à une branche, et inversement.

## 3. Les messages de commit

Forme : **`type(partie): ce que fait la modification`**, au présent, en une phrase courte.

| Type | Quand |
|---|---|
| `feat` | Une nouvelle fonction |
| `fix` | Une correction |
| `test` | Des tests |
| `docs` | De la documentation |
| `ci` | Les contrôles automatiques |
| `refactor` | Du code réorganisé, sans changer ce qu'il fait |
| `chore` | De l'entretien (mise à jour d'une bibliothèque…) |

Exemple : `feat(compte): un spectateur peut créer son compte`.

## 4. Le chemin d'une modification

```
develop ──► feature/e9-us1-compte-spectateur ──► merge request ──► develop ──► main (v2.0.0)
                 code + tests                    tests au vert,
                                                 Sonar au vert,
                                                 DoD cochée
```

1. Partir de la dernière version de `develop` et créer la branche de travail.
2. Coder **avec ses tests** : chaque critère d'acceptation de la carte Trello a son test.
3. Ouvrir une **merge request** (sur GitHub : *pull request*) vers `develop`. GitHub Actions
   lance les tests et SonarCloud contrôle la qualité du code.
4. Fusionner seulement si tout est au vert et si la DoD de la carte est cochée.
5. Pour une nouvelle version : merge request de `develop` vers `main`, puis étiquette `vX.Y.Z`.

## 5. Les règles d'or

1. Jamais de mot de passe ni de clé secrète dans Git (le fichier `.env` est exclu).
2. Une branche = un seul sujet. Petites modifications, petits commits.
3. On lance les tests avant d'envoyer ; GitHub les relance de toute façon.
