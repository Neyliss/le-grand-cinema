# Traçabilité : de la carte Trello au test

Chaque user story du tableau Trello (https://trello.com/b/13VNcnfh) a **sa branche** et **son
fichier de tests**. Dans ce fichier, chaque critère d'acceptation de la carte a **son test**,
nommé `test_critere_N_…` : on retrouve tout de suite quel critère est vérifié, et par quoi.

**Bilan : 15 user stories, 44 critères d'acceptation, 44 critères vérifiés par un test automatique.**

| Story | Titre | Priorité | Branche | Fichier de tests | Critères testés |
|---|---|---|---|---|---|
| E1-US1 | Films et horaires du jour | Must (Sprint 2) | `feature/e1-us1-films-horaires` | [`test_e1_us1_films_horaires.py`](../catalogue/tests/test_e1_us1_films_horaires.py) | 3 / 3 |
| E1-US2 | Site en anglais | Must (Sprint 2) | `feature/e1-us2-site-anglais` | [`test_e1_us2_site_anglais.py`](../catalogue/tests/test_e1_us2_site_anglais.py) | 3 / 3 |
| E2-US1 | Plan de salle en temps réel | Must (Sprint 3) | `feature/e2-us1-plan-temps-reel` | [`test_e2_us1_plan_temps_reel.py`](../reservation/tests/test_e2_us1_plan_temps_reel.py) | 3 / 3 |
| E2-US2 | Bloquer les sièges 10 min | Must (Sprint 3) | `feature/e2-us2-blocage-10-minutes` | [`test_e2_us2_blocage.py`](../reservation/tests/test_e2_us2_blocage.py) | 3 / 3 |
| E3-US1 | Réserver sans créer de compte | Must (Sprint 4) | `feature/e3-us1-reserver-sans-compte` | [`test_e3_us1_reserver_sans_compte.py`](../reservation/tests/test_e3_us1_reserver_sans_compte.py) | 3 / 3 |
| E3-US2 | Payer par carte (Stripe) | Must (Sprint 4) | `feature/e3-us2-payer-par-carte` | [`test_e3_us2_payer_par_carte.py`](../paiement/tests/test_e3_us2_payer_par_carte.py) | 3 / 3 |
| E4-US1 | Recevoir le billet QR par e-mail | Must (Sprint 4) | `feature/e4-us1-billet-qr-email` | [`test_e4_us1_billet_qr_email.py`](../billetterie/tests/test_e4_us1_billet_qr_email.py) | 3 / 3 |
| E5-US1 | Créer une séance | Must (Sprint 1) | `feature/e5-us1-creer-seance` | [`test_e5_us1_creer_seance.py`](../catalogue/tests/test_e5_us1_creer_seance.py) | 3 / 3 |
| E5-US2 | Annuler une séance | Must (Sprint 1) | `feature/e5-us2-annuler-seance` | [`test_e5_us2_annuler_seance.py`](../catalogue/tests/test_e5_us2_annuler_seance.py) | 2 / 2 |
| E6-US1 | Vendre une place au guichet | Must (Sprint 5) | `feature/e6-us1-vente-guichet` | [`test_e6_us1_vente_guichet.py`](../guichet/tests/test_e6_us1_vente_guichet.py) | 3 / 3 |
| E6-US2 | Scanner un billet à l'entrée | Must (Sprint 5) | `feature/e6-us2-controle-billets` | [`test_e6_us2_controle_billets.py`](../billetterie/tests/test_e6_us2_controle_billets.py) | 3 / 3 |
| E7-US1 | Voir le remplissage, exporter | Must (Sprint 5) | `feature/e7-us1-remplissage-export` | [`test_e7_us1_remplissage_export.py`](../pilotage/tests/test_e7_us1_remplissage_export.py) | 3 / 3 |
| E8-US1 | Anticiper les pics d'affluence | Should (V2) | `feature/e8-us1-tableau-festival` | [`test_e8_us1_tableau_festival.py`](../pilotage/tests/test_e8_us1_tableau_festival.py) | 3 / 3 |
| E9-US1 | Gérer un compte spectateur | Should (V2) | `feature/e9-us1-compte-spectateur` | [`test_e9_us1_compte_spectateur.py`](../comptes/tests/test_e9_us1_compte_spectateur.py) | 3 / 3 |
| E10-US1 | Fidéliser les spectateurs (abonnements, offres) | Could (V3) | `feature/e10-us1-abonnement` | [`test_e10_us1_abonnement.py`](../fidelite/tests/test_e10_us1_abonnement.py) | 3 / 3 |

## Les autres branches du bloc 3

| Branche | Contenu |
|---|---|
| `docs/conventions-branches` | règles de nommage des branches et des commits ([conventions](conventions.md)) |
| `feature/api-programmation` | API de la programmation et du plan de salle, documentée dans Swagger ([API](api.md)) |
| `ci/sonarcloud` | contrôle de la qualité du code à chaque envoi ([SonarQube Cloud](guide-sonarcloud.md)) |
| `fix/paiement-seance-annulee` | correction d'un bug : un paiement accepté pour une séance annulée (test d'abord en échec, puis corrigé) |
| `feature/deploiement-aws` | mise en ligne sur Elastic Beanstalk derrière CloudFront ([guide AWS](guide-aws.md)) |
| `docs/base-de-donnees` | modèle de données et script SQL ([base de données](base-de-donnees/README.md)) |
| `docs/tracabilite-tests` | ce document et le guide des tests à jour |
| `fix/affiches-demo` | affiches de démonstration allégées (même image, fichiers 25 % plus légers) |

## Relancer les tests d'une story

```bash
python manage.py test reservation.tests.test_e3_us1_reserver_sans_compte -v 2
```

Le détail de chaque test (son nom se lit comme une phrase) s'affiche ; la dernière ligne doit être `OK`.
