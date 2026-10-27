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

### Calculer les itineraires
```bash
python -m src.cli --donnees data/petit --operation itineraires
python -m src.cli --donnees data/realiste --scenario fermeture_pont_central --operation itineraires
```

### Generer un gros graphe (ex: 1000 sommets)
Graine fixee donc le resultat est toujours le meme :
```bash
python -m src.cli --generer --sommets 1000 --densite 3.0 --graine 42 --sortie data/genere
```

---

## 3. Lancer les tests

23 tests unitaires avec pytest :
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
* `src/indicateurs.py` : simulation des scenarios sur copie et module 5.
* `src/cli.py` : script pour tout lancer en ligne de commande.
* `data/petit/` : petit graphe de 8 sommets avec les resultats attendus calcules a la main.
* `data/realiste/` : ville synthetique de 120 sommets (Novapolis).
