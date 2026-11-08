# Jeu genere - 1000 sites (SYNTHETIQUE)

> **Donnees synthetiques.** Ce jeu est produit par `src/generateur.py`. Les sites, les routes et les couts sont tires au hasard : ils ne decrivent aucune ville reelle.

## Comment le regenerer
Meme graine, meme jeu :
```bash
python3 -m src.cli --generer --sommets 1000 --densite 3.0 --graine 42 --sortie data/genere
```

## Contenu
* `sites.csv` : 1000 sites (`S0001` a `S1000`) places au hasard dans un carre. 34 casernes, 26 hopitaux, 54 centres telecom, 102 ecoles et 784 quartiers.
* `routes.csv` : 3000 arcs orientes. Une chaine relie tous les sites, puis chaque site est relie a ses plus proches voisins. Temps normal en minutes, temps de pointe entre 1,2 et 2,2 fois plus long. 37 arcs sur 3000 (1,2 %) sont en `travaux`.
* `fibre.csv` : chaque site est relie a ses 4 plus proches voisins, avec un cout qui croit avec la distance.
* `demandes.csv` : 50 demandes d'intervention sur des sites tires au hasard.
* `scenarios.csv` : une fermeture de route, l'heure de pointe generale et une panne de fibre.

## Usage
Il sert aux experiences sur les gros graphes (au moins 1000 sommets, comme le demande le sujet). Les benchmarks de `src/benchmarks.py` utilisent en plus des graphes generes en memoire, dont on choisit le nombre d'aretes.
