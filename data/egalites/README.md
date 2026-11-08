# Jeu de test artificiel : égalités de coûts (Module 4)

Ce jeu SYNTHÉTIQUE montre deux arbres couvrants minimaux différents, de même coût. Seule la fibre est utilisée : `routes.csv` ne contient que son en-tête.

Le réseau est un unique cycle : `A - C - E - B - D - A`.

| Tronçon | Coût |
| :--- | :--- |
| `A - C` | 1.0 |
| `A - D` | 1.0 |
| `B - E` | 1.0 |
| `B - D` | 2.0 |
| `C - E` | 2.0 |

Un arbre couvrant s'obtient en retirant exactement un tronçon du cycle. Le coût total du cycle est 7.0 : retirer un tronçon à 2.0 donne un coût de 5.0, retirer un tronçon à 1.0 donne 6.0. Il existe donc exactement 2 arbres couvrants minimaux :

* Kruskal garde `B - D` et rejette `C - E`.
* Prim, parti de `A`, garde `C - E` et rejette `B - D`.

```bash
python3 -m src.cli --donnees data/egalites --operation mst
```
