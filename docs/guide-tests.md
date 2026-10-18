# Guide des tests du projet

Le projet compte **35 tests automatisés**. Ils vérifient les règles du cahier des charges, en
particulier la règle critique « un siège ne se vend qu'une fois ». Ce guide explique comment les
lancer, comment ils sont rangés et quelles bonnes pratiques ils suivent.

---

## 1. Lancer les tests

```bash
python manage.py test                                  # tous les tests (≈ 3 secondes)
python manage.py test reservation                      # un module
python manage.py test reservation.tests.test_double_vente          # un fichier
python manage.py test reservation.tests.test_double_vente.DoubleVenteTests.test_tout_ou_rien_si_un_seul_siege_est_pris   # un seul test
python manage.py test -v 2                             # affiche le nom de chaque test
python manage.py test --shuffle                        # ordre aléatoire (détecte les dépendances cachées)
```

Avec Docker (base PostgreSQL, comme en production) : `docker compose exec web python manage.py test`.

**Lire le résultat** : chaque `.` est un test réussi, `s` un test ignoré (*skipped*), `F` un
test qui échoue, `E` une erreur. La dernière ligne doit être `OK`.

> Avec SQLite, un test est ignoré : celui de la concurrence réelle, qui demande les verrous de
> lignes de PostgreSQL. Avec PostgreSQL (Docker ou Postgres.app), les 35 tests tournent.

## 2. Où sont les tests

Chaque module a un dossier `tests/`, avec **un fichier par sujet**. Le nom commence par `test_`
pour que Django le trouve tout seul.

```
reservation/tests/
├── test_generation_places.py   une place libre par siège à la création d'une séance
├── test_double_vente.py        règle critique, dont 5 spectateurs en même temps (PostgreSQL)
├── test_blocage.py             blocage de 10 minutes et libération
├── test_plan_de_salle.py       plan JSON, séance passée non réservable
└── test_parcours_en_ligne.py   parcours complet : sièges → tarifs → paiement → e-mail avec PDF
paiement/tests/
├── test_checkout.py            session Stripe Checkout (Stripe simulé)
├── test_webhook.py             message signé accepté, faux message refusé, doublon sans effet
└── test_paiement_tardif.py     paiement après le délai : remboursé
billetterie/tests/
├── test_controle.py            billet valide, déjà utilisé, inconnu, non payé, autre séance
└── test_pdf.py                 une page de PDF par billet
catalogue/tests/
├── test_programmation.py       séances du jour, séance annulée retirée
└── test_langues.py             site en anglais, passage FR → EN → FR
guichet/tests/test_vente.py     une vente au guichet retire la place du site
pilotage/tests/test_tableau.py  taux de remplissage, export CSV
grandcinema/tests/test_acces.py droits d'accès du public, des agents et des administrateurs
outils_de_test/fabriques.py     fonctions qui créent les données de test (pas des tests)
```

## 3. Les types de tests présents

| Type | Ce qu'il vérifie | Exemple |
|---|---|---|
| **Unitaire** | Une fonction seule, sans passer par les pages | `test_un_blocage_expire_libere_le_siege` appelle `liberer_places_expirees` |
| **Intégration** | Une page complète : adresse, vue, base, gabarit | `test_le_plan_json_indique_le_statut_de_chaque_siege` |
| **Parcours (bout en bout)** | Un scénario utilisateur entier | `test_reservation_paiement_et_billet` |
| **Concurrence** | Plusieurs utilisateurs au même instant | `test_un_seul_spectateur_obtient_le_siege` |
| **Sécurité** | Refus de ce qui doit être refusé | `test_webhook_avec_fausse_signature_refuse`, `test_pilotage_interdit_aux_agents` |

## 4. Les bonnes pratiques suivies (et pourquoi)

1. **Un test = un comportement, et son nom le dit.**
   `test_billet_valide_puis_refuse_au_second_scan` se lit comme une phrase du cahier des charges.
   Quand il échoue, on sait tout de suite quelle règle est cassée.

2. **Préparer / Agir / Vérifier** (en anglais *Arrange / Act / Assert*). Trois blocs séparés
   par une ligne vide :

   ```python
   def test_un_autre_spectateur_peut_reprendre_un_siege_expire(self):
       premiere = creer_reservation(self.seance, [self.siege.id])                 # Préparer
       premiere.places.update(fin_blocage=timezone.now() - timedelta(seconds=1))

       seconde = creer_reservation(self.seance, [self.siege.id])                  # Agir

       self.assertEqual(seconde.places.get().siege, self.siege)                   # Vérifier
   ```

3. **Des tests indépendants.** Chaque test part d'une base vide et crée ses propres données ;
   il doit réussir seul, avant ou après n'importe quel autre. On le vérifie avec `--shuffle`.
   Exemple réel : en rangeant les tests, l'ordre a changé et un test a échoué, car le test des
   langues laissait l'anglais actif pour le suivant. La correction (`tearDown` qui remet le
   français) est dans `catalogue/tests/test_langues.py`.

4. **Des fabriques plutôt que du copier-coller.** `outils_de_test/fabriques.py` crée une séance,
   une vente ou un compte en une ligne : `creer_seance()`, `vendre(seance, nb=3)`,
   `creer_agent()`. Si le modèle change, on corrige un seul endroit.

5. **Aucun accès à Internet.** Stripe est remplacé par un « double » (`unittest.mock`) et les
   messages du webhook sont signés dans le test, comme le ferait Stripe. Les tests sont rapides,
   gratuits et ne dépendent pas d'un service extérieur.

6. **Tester les refus, pas seulement les succès.** Faux webhook, billet déjà utilisé, siège déjà
   pris, agent qui tente d'ouvrir le pilotage : ce sont souvent là que se cachent les failles.

7. **Une sortie propre.** Les messages de journal attendus (refus du webhook, page 404) sont
   capturés et vérifiés avec `assertLogs` au lieu de s'afficher au milieu des résultats.

8. **Un test doit pouvoir échouer.** Le test de concurrence a été vérifié en retirant le verrou
   `select_for_update` : il échoue alors (3 spectateurs sur 5 obtiennent le même siège). Un test
   qui passe quoi qu'il arrive ne protège rien.

9. **Tester sur la même base que la production.** SQLite suffit pour aller vite ; PostgreSQL
   (Docker ou intégration continue) révèle les vrais comportements, comme les verrous de lignes.

10. **Les tests tournent à chaque envoi sur GitHub** (onglet *Actions*), en ordre aléatoire,
    sur PostgreSQL et dans Docker. Une fusion dans `develop` ou `main` ne se fait qu'avec la
    coche verte.

## 5. Mesurer la couverture

La couverture indique la part du code exécutée par les tests.

```bash
pip install -r requirements-dev.txt
coverage run manage.py test
coverage report            # tableau dans le terminal
coverage html              # rapport détaillé : ouvrir htmlcov/index.html
```

Aujourd'hui : **76 %**. L'intégration continue refuse de descendre sous 75 %.
Parties peu couvertes, pistes pour de prochains tests : la commande `charger_demo` (données de
démonstration), la commande `liberer_places`, les pages de retour de Stripe et de paiement
simulé, l'action « annuler » de l'administration.

> La couverture est un indicateur, pas un but : 100 % de lignes exécutées ne garantit pas que
> les bonnes choses sont vérifiées. On vise d'abord les règles métier et les cas de refus.

## 6. Écrire un nouveau test

1. Choisir le fichier du sujet (ou en créer un nouveau, nommé `test_<sujet>.py`, dans le
   dossier `tests/` du module).
2. Écrire une classe qui hérite de `TestCase` et une méthode dont le nom commence par `test_`.
3. Utiliser les fabriques pour les données, puis Préparer / Agir / Vérifier.
4. Lancer le test, le voir **échouer** si le code n'existe pas encore, écrire le code, le voir
   **réussir**.

```python
"""RG-03 : une réservation contient au plus 8 places."""
from django.test import TestCase

from outils_de_test.fabriques import creer_seance
from reservation.services import SiegeIndisponible, creer_reservation


class LimiteDePlacesTests(TestCase):
    def test_neuf_places_refusees(self):
        seance = creer_seance(rangees=3, par_rangee=5)
        neuf_sieges = [s.id for s in seance.salle.sieges.all()[:9]]

        with self.assertRaises(SiegeIndisponible):
            creer_reservation(seance, neuf_sieges)
```
