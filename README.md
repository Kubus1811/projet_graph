# Projet Novapolis Resilience - Partie A

Projet d'algorithmique des graphes.
Partie A : classe Graphe, lecture et validation des CSV, scenarios sur copie, generateur aleatoire et CLI.

---

## 1. Installation

Pour lancer le projet :

```bash
# installer les bibliotheques necessaires
pip install -r requirements.txt
```

---

## 2. Commandes rapides (CLI)

Tout se lance avec `python -m src.cli` :

### Valider les fichiers CSV
Verifie qu'il n'y a pas d'erreurs (doublons, sites inconnus, temps negatifs...) :
```bash
python -m src.cli --donnees data/petit --operation valider
python -m src.cli --donnees data/realiste --operation valider
```

### Lancer la resilience (Module 5)
Compare les 3 scenarios (normal, axe ferme, panne fibre) et sort un tableau :
```bash
python -m src.cli --donnees data/petit --operation resilience
python -m src.cli --donnees data/realiste --operation resilience
```

### Diagnostic d'accessibilite (Module 1)
BFS multi-casernes, sites non atteignables / isoles, composantes connexes et fortement connexes, circuit :
```bash
python -m src.cli --donnees data/petit --operation accessibilite
python -m src.cli --donnees data/realiste --operation accessibilite
python -m src.cli --donnees data/genere --operation accessibilite
```

### Calculer les itineraires (Module 2)
Sans scenario : caserne la plus proche et chemin pour chaque demande, plus verification que Dijkstra, Bellman-Ford et Floyd-Warshall concordent.
Avec scenario : cout avant/apres, retard absolu et relatif, nouveau chemin et indicateurs routes.
```bash
python -m src.cli --donnees data/petit --operation itineraires
python -m src.cli --donnees data/petit --scenario fermeture_route_C1_Q1 --operation itineraires
python -m src.cli --donnees data/realiste --scenario fermeture_pont_central --operation itineraires
python -m src.cli --donnees data/realiste --scenario heure_pointe_generale --operation itineraires
```

### Visualisation graphique (pygame)
Fenetre interactive : clic gauche = source, clic droit = cible, `1/2/3` = Dijkstra / Bellman-Ford / Floyd-Warshall,
`S` = scenario suivant (route fermee en pointille rouge), `M` = mode (chemin, accessibilite, CFC, itineraires),
`Espace` = animation de l'exploration, molette = zoom, `H` = aide.
```bash
python -m src.visu --donnees data/petit
python -m src.visu --donnees data/realiste --source CAS_01 --cible QUA_007
# image PNG sans ouvrir de fenetre (pour le rapport)
python -m src.visu --donnees data/petit --source C1 --cible Q1 --scenario fermeture_route_C1_Q1 --capture resultats/visu_petit_fermeture.png
```

### Generer un gros graphe (ex: 1000 sommets)
Graine fixee donc le resultat est toujours le meme :
```bash
python -m src.cli --generer --sommets 1000 --densite 3.0 --graine 42 --sortie data/genere
```

---

## 3. Lancer les tests

85 tests unitaires avec pytest :
```bash
pytest tests/ -v
```

---

## 4. Organisation des fichiers CSV

* `sites.csv` : `id,nom,type,longitude,latitude` (liste des sommets)
* `routes.csv` : `u,v,temps_normal,temps_pointe,statut` (graphe oriente pour les voitures)
* `fibre.csv` : `u,v,cost,statut` (graphe non oriente pour la fibre optique)
* `demandes.csv` : `id,origine,type,priorite` (urgences a secourir)
* `scenarios.csv` : `scenario,action,u,v,valeur` (fermer_route, modifier_temps, heure_pointe, fermer_fibre)

---

## 5. Structure du code

* `src/graphe.py` : classe Graphe en listes d'adjacence et methode copie profonde.
* `src/io_donnees.py` : lecture/ecriture CSV et validateur qui bloque les erreurs.
* `src/generateur.py` : generation de ville aleatoire avec graine.
* `src/parcours.py` : DFS et BFS iteratifs, accessibilite multi-casernes, circuits (DFS 3 couleurs), Kosaraju (B).
* `src/chemins.py` : Dijkstra (tas binaire), Bellman-Ford (detection et -inf), Floyd-Warshall, itineraires par demande, scenarios de fermeture (B).
* `src/visu.py` : visualisation pygame (positions et fleches calculees avec `pygame.math.Vector2`).
* `src/indicateurs.py` : simulation des scenarios sur copie et module 5.
* `src/cli.py` : script pour tout lancer en ligne de commande.
* `data/petit/` : petit graphe de 8 sommets avec les resultats attendus calcules a la main.
* `data/realiste/` : ville synthetique de 120 sommets (Novapolis).
