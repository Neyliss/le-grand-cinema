# La base de données

La base est **PostgreSQL** (Amazon RDS en ligne, Docker en local). Elle contient 14 tables.
Les cinq demandées sont en **trait épais** sur le schéma : utilisateurs, films, séances,
réservations et places.

![Diagramme de classes UML : les 14 tables](classes-uml.png)

**Lire le schéma** (diagramme de classes UML, comme au bloc 1) : chaque boîte est une table, avec ses
attributs et leur type. Les chiffres au bout d'un lien disent « combien » : `1` exactement un,
`0..1` zéro ou un, `0..*` zéro ou plusieurs, `1..*` au moins un. Exemple : une séance a **une
place par siège** (`1` → `1..*`), et une place appartient à **une seule** séance. Le losange
noir est une composition : la place n'existe pas sans sa séance. En rouge : les règles imposées
par la base.

| Fichier | Contenu |
|---|---|
| `../schemas/Le_Grand_Cinema_schemas.drawio`, page « Bloc 3 · Figure 2 » | le schéma ci-dessus, à ouvrir dans draw.io ([lien sans compte](https://viewer.diagrams.net/?nav=1&title=Le_Grand_Cinema_schemas.drawio#Uhttps%3A%2F%2Fraw.githubusercontent.com%2FNeyliss%2Fle-grand-cinema%2Fdevelop%2Fdocs%2Fschemas%2FLe_Grand_Cinema_schemas.drawio)) ; `classes-uml.png` en est l'image |
| `modele-de-donnees.png` (source `.mmd`) | le même modèle vu comme les tables de la base (identifiants `PK`, valeurs uniques `UK`) |
| `schema.sql` | le script SQL commenté de toutes les tables, liens et règles |

## Les cinq tables demandées

| Table | Une ligne = | Ce qui compte |
|---|---|---|
| `auth_user` | un utilisateur (personnel ou spectateur avec compte) | mot de passe jamais en clair (empreinte) |
| `catalogue_film` | un film | durée, version VF/VOST, film du festival |
| `catalogue_seance` | une projection d'un film dans une salle | début, statut (publiée ou annulée) |
| `reservation_reservation` | une commande (site ou guichet) | référence unique, compte **facultatif** |
| `reservation_placeseance` | un siège pour une séance | statut libre / bloquée / vendue |

## Les règles portées par la base

1. **Un siège ne se vend qu'une fois** : la contrainte `place_unique_par_seance (seance_id, siege_id)`
   rend un doublon impossible, même si le site et le guichet vendent au même moment.
2. **Un siège existe une seule fois dans sa salle** : `siege_unique_par_salle`.
3. **Un billet par place**, avec un code QR unique ; **un paiement par réservation**.
4. **Une carte d'abonnement ne descend jamais sous zéro** : `CHECK (places_restantes >= 0)`.
5. **Réserver sans compte** : `compte_id` peut rester vide.
6. **RGPD** : supprimer un compte vide le lien (`SET NULL`) sans effacer les ventes, qui restent
   pour la comptabilité, sans nom ni adresse.
7. **Pas de donnée bancaire** : seulement la référence du paiement chez Stripe.

## D'où vient ce script, et comment il est vérifié

Les tables sont créées par Django à partir des modèles (`models.py` de chaque partie), avec
`python manage.py migrate`. Le script `schema.sql` en est la version lisible. Il a été exécuté sur
PostgreSQL 16 puis comparé aux tables créées par Django : **mêmes 98 colonnes, mêmes 30
contraintes (clés, valeurs uniques, contrôles) et mêmes 15 liens**.

```bash
createdb verif && psql -d verif -f docs/base-de-donnees/schema.sql   # le script s'exécute sans erreur
```

Les règles « que faire quand on supprime » (`ON DELETE`) sont celles des modèles Django
(`on_delete=`) : `RESTRICT` (interdit, ex. supprimer un film qui a des séances), `CASCADE`
(supprime aussi, ex. les places d'une séance) et `SET NULL` (garde la ligne, sans le lien).
