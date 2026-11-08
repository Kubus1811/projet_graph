# Jeux de test artificiels : circuits absorbants (Module 3)

> **Données SYNTHÉTIQUES.** Les coûts négatifs de ces jeux ne représentent pas des durées réelles : un temps de trajet n'est jamais négatif. Ils servent uniquement à vérifier Bellman-Ford, Floyd-Warshall et la détection des circuits absorbants. Les scénarios métier de Novapolis n'ont aucun circuit absorbant.

Ces jeux sont refusés par la validation par défaut. Ils se chargent avec :

```python
charger_jeu_donnees("data/absorbants/accessible", autoriser_temps_negatifs=True)
```

Seul `routes.csv` sert au test : `fibre.csv` ne contient que son en-tête. Les réponses attendues sont dans `resultats_attendus.json` de chaque dossier (`"inf"` : inaccessible, `"-inf"` : diminuable indéfiniment).

## `accessible/` : circuit atteignable depuis S1

Circuit `S2 -> S3 -> S4 -> S2`, coût 2 + 3 - 6 = -1.

```
S8 -> S1 -> S2 -> S3 -> S4 -> S5
      |      ^___(-6)___|
      v
      S6 -> S7
```

| Sommet | Distance depuis S1 | Pourquoi |
| :--- | :--- | :--- |
| `S1` | 0 | Le circuit ne revient jamais à S1 |
| `S2`, `S3`, `S4` | -inf | Sur le circuit |
| `S5` | -inf | Pas sur le circuit, mais atteignable après lui |
| `S6`, `S7` | 4 et 6 | Atteignables, mais jamais après le circuit |
| `S8` | inf | Aucun arc n'y mène |

Depuis `S5`, le même graphe ne donne accès à aucun circuit : `S5` n'a pas de successeur. La réponse dépend donc de la source.

## `non_accessible/` : circuit hors de portée de S1

Circuit `S4 -> S5 -> S6 -> S4`, coût 1 + 1 - 4 = -2.

```
S1 -> S2 -> S3
            ^
            | (arc de sortie S5 -> S3)
      S4 -> S5 -> S6
      ^___(-4)___|
```

* Depuis `S1` : Bellman-Ford ne voit pas le circuit et les distances restent finies (`S3` = 5).
* Le circuit existe quand même : la super-source (reliée à tous les sommets, coût 0) ou la diagonale de Floyd-Warshall (`L[i][i] < 0`) le détectent.
* Piège : l'arc `S5 -> S3` permet à une super-source de diminuer `S3` indéfiniment. Cette valeur ne doit pas être reportée sur la distance depuis `S1`.
* Depuis `S4` : le circuit devient accessible et `S3` passe à -inf.
