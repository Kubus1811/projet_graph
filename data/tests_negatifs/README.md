# Jeu de test artificiel avec circuit absorbant (Module 3)

Ce jeu de test contient un circuit absorbant (coûts négatifs) permettant de valider les algorithmes de Bellman-Ford et Floyd-Warshall.

* Circuit négatif : S2 -> S3 -> S4 -> S2 (coût total : 2.0 + 3.0 - 6.0 = -1.0 < 0).
* Accessible depuis S1 (caserne).
* Doit être chargé avec l'option `autoriser_temps_negatifs=True`.
