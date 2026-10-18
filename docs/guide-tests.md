# Les tests : le guide simple

Un **test** est un petit programme qui vérifie tout seul qu'une règle du projet est respectée.
Par exemple : « un siège ne peut pas être vendu deux fois ». Le projet en compte **41**. On les
lance en une commande, et ils répondent en quelques secondes.

À quoi ça sert ? À **modifier le code sans peur** : si une modification casse une règle, un
test le signale tout de suite, avant que les spectateurs ne s'en rendent compte.

---

## 1. Lancer les tests

```bash
python manage.py test
```

Avec Docker : `docker compose exec web python manage.py test`.

Quelques variantes utiles :

| Je veux… | Commande |
|---|---|
| Tester un seul module | `python manage.py test reservation` |
| Tester un seul fichier | `python manage.py test reservation.tests.test_blocage` |
| Voir le nom de chaque test | `python manage.py test -v 2` |
| Mélanger l'ordre des tests | `python manage.py test --shuffle` |

## 2. Lire le résultat

- Chaque **point** `.` est un test réussi.
- Un **`s`** est un test ignoré (*skipped*). Avec SQLite, le test « 5 spectateurs en même temps »
  est ignoré, car il a besoin de PostgreSQL. Avec Docker, il tourne.
- Un **`F`** ou un **`E`** est un test qui échoue : le détail s'affiche en dessous.
- La dernière ligne doit être **`OK`**.

## 3. Où sont les tests

Chaque partie du site a un dossier `tests/`. Dedans, **un fichier par sujet**, dont le nom
commence par `test_` :

```
reservation/tests/   règle « un siège, une vente », blocage de 10 minutes, plan de salle, parcours complet
paiement/tests/      paiement Stripe, confirmation signée, paiement en retard
billetterie/tests/   contrôle des billets à l'entrée, billet PDF
catalogue/tests/     programmation, site en anglais, données de démonstration
guichet/tests/       vente au guichet
pilotage/tests/      tableau de remplissage, export CSV
grandcinema/tests/   qui a le droit d'ouvrir quelle page
outils_de_test/      petites fonctions qui créent les données des tests
```

## 4. Les bonnes pratiques suivies

**1. Le nom du test dit ce qu'il vérifie.**
`test_billet_valide_puis_refuse_au_second_scan` se lit comme une phrase. S'il échoue, on sait
tout de suite quelle règle est cassée.

**2. Un test vérifie une seule chose.**

**3. Chaque test a trois parties : préparer, agir, vérifier.**

```python
def test_un_autre_spectateur_peut_reprendre_un_siege_expire(self):
    # Préparer : un premier spectateur a bloqué le siège, mais ses 10 minutes sont passées
    premiere = creer_reservation(self.seance, [self.siege.id])
    premiere.places.update(fin_blocage=timezone.now() - timedelta(seconds=1))

    # Agir : un second spectateur demande le même siège
    seconde = creer_reservation(self.seance, [self.siege.id])

    # Vérifier : il l'obtient
    self.assertEqual(seconde.places.get().siege, self.siege)
```

**4. Les tests ne dépendent pas les uns des autres.** Chaque test part d'une base vide et crée
ses propres données. On le vérifie en mélangeant l'ordre (`--shuffle`). Cela a permis de trouver
un vrai défaut : un test laissait le site en anglais pour le test suivant. C'est corrigé.

**5. Les données de test se créent en une ligne**, avec les fonctions de
`outils_de_test/fabriques.py` : `creer_seance()`, `vendre(seance, nb=3)`, `creer_agent()`…

**6. Pas d'Internet pendant les tests.** Stripe est remplacé par une imitation. Les tests sont
donc rapides, gratuits et marchent même hors connexion.

**7. On teste aussi ce qui doit être refusé** : un faux message de paiement, un billet scanné
deux fois, un agent qui essaie d'ouvrir une page réservée à la direction.

**8. Un test doit pouvoir échouer.** Le test des 5 spectateurs a été vérifié en retirant la
protection du code : il échoue alors, car 3 spectateurs sur 5 obtiennent le même siège.
Avec la protection, un seul l'obtient.

**9. GitHub relance tous les tests à chaque envoi** (onglet **Actions**), sur PostgreSQL et
dans Docker. On ne fusionne une modification que si tout est vert.

## 5. La couverture

La **couverture** dit quelle part du code est exécutée pendant les tests.

```bash
pip install -r requirements-dev.txt
coverage run manage.py test
coverage report
```

Aujourd'hui : **85 %**. GitHub refuse une modification qui ferait descendre ce chiffre sous 75 %.
Attention : un chiffre élevé ne suffit pas. Ce qui compte, c'est de tester les règles
importantes et les cas de refus.

## 6. Écrire un nouveau test

1. Ouvrir le dossier `tests/` de la bonne partie du site.
2. Créer un fichier `test_<sujet>.py` (ou compléter un fichier existant).
3. Écrire une classe et une fonction dont le nom commence par `test_`.
4. Lancer le test.

Exemple, pour la règle « 8 places au maximum par réservation » :

```python
from django.test import TestCase

from outils_de_test.fabriques import creer_seance
from reservation.services import SiegeIndisponible, creer_reservation


class LimiteDePlacesTests(TestCase):
    def test_neuf_places_refusees(self):
        # Préparer : une salle de 15 sièges, on en choisit 9
        seance = creer_seance()
        neuf_sieges = [s.id for s in seance.salle.sieges.all()[:9]]

        # Agir et vérifier : la réservation est refusée
        with self.assertRaises(SiegeIndisponible):
            creer_reservation(seance, neuf_sieges)
```
