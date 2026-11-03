# L'API du Grand Cinéma

L'API donne accès aux mêmes données que le site, au format JSON, pour une future application
mobile ou un partenaire (office de tourisme…). Elle applique **les mêmes règles** que les pages :
le code des règles est partagé (`services.py`), il n'est pas recopié.

## La documentation interactive (Swagger)

- **Swagger** : `/api/docs/` — chaque route y est décrite et peut être essayée dans le navigateur.
- **Schéma OpenAPI** (le fichier lu par Swagger) : `/api/schema/`.

La documentation est **générée à partir du code** (drf-spectacular) : elle reste à jour toute seule.
Un test vérifie qu'elle s'affiche (`comptes/tests/test_api_comptes.py`).

## Les routes

| Route | Méthode | Compte | Rôle |
|---|---|---|---|
| `/api/films/` | GET | non | Films à l'affiche |
| `/api/seances/?jour=AAAA-MM-JJ&film=N` | GET | non | Séances à venir et places libres |
| `/api/seances/{id}/plan/` | GET | non | Plan de salle en temps réel |
| `/api/comptes/` | POST | non | Créer un compte spectateur |
| `/api/comptes/confirmer/` | POST | non | Confirmer l'adresse e-mail |
| `/api/comptes/jeton/` | POST | non | Se connecter : renvoie un jeton |
| `/api/comptes/moi/` | GET, DELETE | **jeton** | Voir ou supprimer son compte (RGPD) |
| `/api/comptes/moi/reservations/` | GET | **jeton** | Ses réservations |

## Utiliser un jeton

```bash
# 1. Se connecter : l'API renvoie {"jeton": "..."}
curl -X POST https://<site>/api/comptes/jeton/ -H "Content-Type: application/json" \
     -d '{"email": "spectateur.demo@exemple.fr", "mot_de_passe": "spectateur-gc-2026"}'

# 2. Envoyer le jeton avec chaque demande
curl https://<site>/api/comptes/moi/reservations/ -H "Authorization: Token <jeton>"
```

Dans Swagger : bouton **Authorize**, puis saisir `Token <jeton>` dans la case *tokenAuth*.

## Sécurité

- Les routes « moi » refusent toute demande sans jeton valable (erreur 401).
- Au-delà de 20 essais par minute, la connexion et la création de compte sont bloquées (erreur 429).
- Une erreur de saisie renvoie un message clair (erreur 400) ; un compte déjà existant, l'erreur 409.
