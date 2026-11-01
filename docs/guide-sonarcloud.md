# SonarQube Cloud : le contrôle de la qualité du code

**SonarQube Cloud** (sonarcloud.io, anciennement SonarCloud) relit tout le code à chaque
modification et signale :

| Ce qu'il cherche | Exemple |
|---|---|
| **Bugs** | une variable utilisée avant d'avoir une valeur |
| **Vulnérabilités** et **points sensibles** | un mot de passe écrit dans le code |
| **Mauvaises odeurs** (code difficile à maintenir) | une fonction trop longue ou trop compliquée |
| **Duplications** | le même bloc de code copié à deux endroits |
| **Couverture** | la part du code vérifiée par les tests |

Il donne un verdict : la **porte qualité** (*Quality Gate*). Elle est **verte** si le code
nouveau ne contient aucun problème important et s'il est couvert par des tests à 80 % au moins.
C'est **gratuit pour un dépôt public**, avec l'offre **OSS** (open source) : aucune carte bancaire
n'est demandée. Ne pas choisir l'offre *Team* ni son essai de 14 jours : elle est payante ensuite.

## Comment c'est branché

```
git push ─► GitHub Actions ─► tests + couverture (coverage.xml) ─► SonarQube Cloud ─► verdict
                                                                     sur la pull request
```

- `sonar-project.properties` : le nom du projet, ce qui est analysé, où trouver la couverture.
- `.github/workflows/ci.yml` : après les tests, l'étape « Analyse de la qualité du code » envoie
  le code et le rapport de couverture. Elle ne se lance que si la clé `SONAR_TOKEN` existe.
- En plus, **ruff** vérifie le code au début de chaque passage (variable ou import inutilisé,
  erreur de syntaxe) ; on peut le lancer sur son poste : `ruff check --select F,E9 .`

## Mise en place (une seule fois, 10 minutes)

1. Aller sur **https://sonarcloud.io** et cliquer sur **Log in** puis **GitHub**.
2. Créer l'organisation gratuite : **+** (en haut à droite) > **Create new organization** > **GitHub** >
   le compte *Neyliss* ; donner accès au dépôt **le-grand-cinema**. À l'étape du choix de l'offre,
   ne sélectionner **aucune** offre payante : descendre en bas de la page et cliquer sur
   **Get SonarQube for OSS** (gratuit pour les dépôts publics), puis **Create organization**.
   Si une page demande une carte bancaire ou un nombre de lignes de code, c'est l'offre payante :
   cliquer sur **Exit** et recommencer.
   Ensuite : **+** > **Analyze new project**, cocher **le-grand-cinema**, puis **Set Up**.
3. Choisir la façon d'analyser : **With GitHub Actions** (et non l'analyse automatique).
   SonarQube Cloud affiche alors une **clé** (`SONAR_TOKEN`) : la copier.
4. Sur GitHub, dans le dépôt : **Settings > Secrets and variables > Actions > New repository
   secret**. Nom : `SONAR_TOKEN`. Valeur : la clé copiée. Enregistrer.
   *La clé n'est jamais écrite dans le code : GitHub la garde secrète.*
5. Vérifier que la **clé du projet** et l'**organisation** affichées par SonarQube Cloud
   (*Administration > Information*) sont celles de `sonar-project.properties`
   (`Neyliss_le-grand-cinema` et `neyliss`). Sinon, corriger le fichier.
6. Relancer les tests : onglet **Actions** du dépôt, dernier passage, **Re-run all jobs**.
   Le résultat apparaît sur sonarcloud.io, et sur chaque pull request.

## Lire le résultat

- **Overview** : la porte qualité (verte ou rouge) et les chiffres du code nouveau.
- **Issues** : la liste des problèmes, avec la ligne de code et l'explication de la règle.
- **Security Hotspots** : des points à **examiner** (pas forcément des erreurs). Pour chacun,
  choisir *Safe* (sans risque, avec une phrase d'explication) ou *Fix* (à corriger).
  Exemples attendus dans ce projet :
  - le tirage au hasard des données de démonstration (`charger_demo`) : sans risque, ce ne sont
    que des données d'exemple ;
  - la clé de développement de `settings.py` : sans risque, le site refuse de démarrer en
    production sans sa vraie clé secrète.

## La règle du projet

Une merge request vers `develop` n'est fusionnée que si **les tests et la porte qualité sont
verts** (voir [conventions](conventions.md)). Pour l'imposer : GitHub, **Settings > Branches >
Add rule** sur `develop`, cocher *Require status checks to pass* et choisir
*Tests (PostgreSQL)* et *SonarCloud Code Analysis*.
