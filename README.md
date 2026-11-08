# Projet Novapolis Resilience

Projet d'algorithmique des graphes (trinome) : un outil reproductible qui analyse le reseau routier et le reseau de fibre d'une ville synthetique, applique des perturbations sur une copie et mesure leurs effets.

* Partie A : classe Graphe, lecture et validation des CSV, scenarios sur copie, generateur aleatoire et CLI.
* Partie B : parcours, plus courts chemins, itineraires des secours et visualisation.
* Partie C : arbres couvrants, pannes de fibre, circuits absorbants, benchmarks et site local.

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
Compare les 3 scenarios (normal, axe ferme, panne fibre) et ecrit un tableau dans `resultats/tableau_resilience_<jeu>.md` et `.csv` :
```bash
python -m src.cli --donnees data/petit --operation resilience
python -m src.cli --donnees data/realiste --operation resilience
python -m src.cli --donnees data/genere --operation resilience
```
Sans `--scenario`, le programme prend la premiere fermeture de route et la premiere panne de fibre de `scenarios.csv`. Avec `--scenario`, il compare la situation normale a ce scenario (fichiers `tableau_resilience_<jeu>_<scenario>`) :
```bash
python -m src.cli --donnees data/realiste --scenario fermeture_axe_CAS_04_QUA_084 --operation resilience
python -m src.cli --donnees data/realiste --scenario panne_fibre_CAS_04_QUA_084 --operation resilience
```
Un scenario inconnu est refuse avec la liste des scenarios disponibles.

### Test de resistance (points faibles)
Coupe une a une chaque route empruntee par un itineraire et chaque troncon de l'arbre de fibre, classe les degats, puis compare les facons de rouvrir une route quand les 3 plus critiques sont coupees. Ecrit `resultats/points_faibles_<jeu>.csv` :
```bash
python -m src.cli --donnees data/realiste --operation points_faibles
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

### Regenerer le jeu realiste
Reecrit `data/realiste` a l'identique (graine fixee dans le script) :
```bash
python -m src.creer_jeu_realiste
```

### Calculer l'arbre couvrant de la fibre (Kruskal et Prim)
```bash
python -m src.cli --donnees data/petit --operation mst
python -m src.cli --donnees data/egalites --operation mst
python -m src.cli --donnees data/petit --scenario panne_fibre_troncon_central --operation mst
```

### Detecter les circuits absorbants (Module 3)
Bellman-Ford depuis les casernes (ou `--source`), super-source pour un circuit hors de portee, diagonale de Floyd-Warshall. Les couts negatifs de ces jeux sont artificiels :
```bash
python -m src.cli --donnees data/absorbants/accessible --operation absorbant
python -m src.cli --donnees data/absorbants/non_accessible --operation absorbant
python -m src.cli --donnees data/absorbants/non_accessible --source S4 --operation absorbant
```

### Analyser une panne de fibre et sa reparation
```bash
python -m src.cli --donnees data/petit --operation panne
python -m src.cli --donnees data/realiste --scenario panne_fibre_backbone_sud --operation panne
```

### Lancer les benchmarks
Mesure Kruskal, Prim, BFS, DFS, Dijkstra et Bellman-Ford sur les memes graphes, et Floyd-Warshall jusqu'a 400 sommets. Ecrit les CSV et les graphiques dans `resultats/` (1 a 2 minutes par commande selon la machine) :
```bash
python -m src.cli --operation bench
python -m src.cli --operation localite
```

### Ouvrir le site web local
Aucune installation en plus n'est necessaire :
```bash
python -m src.cli --operation site
```
`--port` change de port, Ctrl+C arrete le serveur.

* http://127.0.0.1:8000 : **La nuit de l'orage**, histoire interactive. Elle commence par la ronde de controle (module 1 de B et verification que ses 3 algorithmes concordent). On joue le regulateur d'une nuit de crise et chaque decision est comparee a l'optimum calcule. L'histoire est inventee, les chiffres sont calcules par le programme.
* http://127.0.0.1:8000/salle : **salle de crise**, mode libre. On coupe une route ou un troncon de fibre sur la carte et tout est recalcule. Quatre onglets :
  * **Crise** : itineraires des demandes, indicateurs du module 5 et points faibles du reseau (test de resistance).
  * **Itineraire** (visualisation de B) : clic sur un depart puis une arrivee, choix de Dijkstra, Bellman-Ford ou Floyd-Warshall, verification que les trois concordent et animation de l'exploration, vehicule qui parcourt le chemin.
  * Sur toute la carte, comme dans `visu.py` de B : routes a sens unique flechees, durees modifiees en orange, case **Durees des routes** (la longueur d'un trait n'est pas sa duree), zoom avec les boutons, Ctrl + molette ou en pincant le pave tactile, deplacement en glissant.
  * **Accessibilite** (module 1 de B) : chaque site prend la couleur de la caserne qui l'atteint en premier (BFS multi-sources).
  * **Connexite** (module 1 de B) : composantes connexes et fortement connexes, exemple de circuit oriente.

Technologies du site : ville isometrique dessinee en Canvas 2D sans bibliotheque, synthese vocale du navigateur (Web Speech) et sons generes (Web Audio) pour la radio, serveur Python standard (`http.server`).

---

## 3. Lancer les tests

Tests unitaires avec pytest :
```bash
pytest tests/ -v
```

---

## 4. Organisation des fichiers CSV

Fichiers en UTF-8 avec une ligne d'en-tete. Toutes les colonnes sont obligatoires. Le validateur refuse les valeurs hors de ces regles en indiquant le fichier et la ligne (`python -m src.cli --donnees <dossier> --operation valider`).

**Toutes les donnees sont synthetiques.** Aucune donnee externe n'est utilisee : il n'y a ni source ni licence a citer.

### `sites.csv` : les sommets des deux reseaux

| Champ | Type | Signification |
| :--- | :--- | :--- |
| `id` | texte unique | identifiant du site |
| `nom` | texte | nom affiche |
| `type` | texte | `caserne`, `hopital`, `telecom`, `ecole` ou `quartier`. Les sites sensibles sont `hopital`, `ecole` et `telecom` |
| `longitude`, `latitude` | decimal (degres), vide = 0 | position, utilisee pour le dessin |

### `routes.csv` : graphe oriente, un arc = un trajet autorise

| Champ | Type | Signification |
| :--- | :--- | :--- |
| `u`, `v` | `id` de site | arc de `u` vers `v`. Un couple (`u`, `v`) n'apparait qu'une fois |
| `temps_normal` | decimal >= 0 (minutes) | duree hors pointe |
| `temps_pointe` | decimal >= `temps_normal` (minutes) | duree en heure de pointe |
| `statut` | `ouvert`, `ferme` ou `travaux`, vide = `ouvert` | `ferme` : route inutilisable. `travaux` : route praticable, signalee dans l'itineraire |

### `fibre.csv` : graphe non oriente, une arete = un troncon realisable

| Champ | Type | Signification |
| :--- | :--- | :--- |
| `u`, `v` | `id` de site | `u - v` et `v - u` designent le meme troncon, qui n'apparait qu'une fois |
| `cost` | decimal >= 0 (k€) | cout de construction |
| `statut` | `ouvert`, `ferme` ou `travaux`, vide = `ouvert` | un troncon `ferme` ou en `travaux` n'est jamais utilise |

### `demandes.csv` : urgences a secourir

| Champ | Type | Signification |
| :--- | :--- | :--- |
| `id` | texte unique | identifiant de la demande |
| `origine` | `id` de site | lieu de l'intervention |
| `type` | texte | nature de l'urgence, informatif |
| `priorite` | `critique`, `haute`, `normale` ou `basse` | informatif, pas utilise par les calculs |

### `scenarios.csv` : une ligne par action, les lignes de meme nom forment un scenario

| Champ | Type | Signification |
| :--- | :--- | :--- |
| `scenario` | texte non vide | nom du scenario, a passer a `--scenario` |
| `action` | voir ci-dessous | perturbation a appliquer |
| `u`, `v` | `id` de site | route ou troncon vise, qui doit exister. Vides pour `heure_pointe` |
| `valeur` | decimal >= 0 (minutes) | nouveau temps pour `modifier_temps`, vide sinon |

* `fermer_route` : supprime l'arc `u -> v` (un seul sens) du reseau routier.
* `modifier_temps` : remplace le temps de l'arc `u -> v`.
* `heure_pointe` : applique `temps_pointe` a toutes les routes.
* `fermer_fibre` : coupe le troncon `u - v` du reseau de fibre, sans toucher aux routes.

Les perturbations s'appliquent toujours sur une copie : les donnees de reference ne changent jamais.

---

## 5. Structure du code

* `src/graphe.py` : classe Graphe en listes d'adjacence et methode copie profonde.
* `src/io_donnees.py` : lecture/ecriture CSV et validateur qui bloque les erreurs.
* `src/generateur.py` : generation de ville aleatoire avec graine.
* `src/creer_jeu_realiste.py` : construction du jeu `data/realiste`, avec graine fixee.
* `src/parcours.py` : DFS et BFS iteratifs, accessibilite multi-casernes, circuits (DFS 3 couleurs), Kosaraju (B).
* `src/chemins.py` : Dijkstra (tas binaire), Bellman-Ford (detection et -inf), Floyd-Warshall, itineraires par demande, scenarios de fermeture (B).
* `src/visu.py` : visualisation pygame (positions et fleches calculees avec `pygame.math.Vector2`).
* `src/indicateurs.py` : simulation des scenarios sur copie et module 5.
* `src/cli.py` : script pour tout lancer en ligne de commande.
* `src/arbres.py` : Union-Find, Kruskal, Prim, composantes, pannes et reparations de la fibre.
* `src/benchmarks.py` : mesures, graphiques et experience sur la memoire.
* `src/salle_de_crise.py` : simulation des coupures et recherche des points faibles.
* `src/recit.py` : construit l'histoire et ses decisions a partir des calculs.
* `src/site_web.py`, `src/recit.html` et `src/salle_de_crise.html` : serveur local et pages du site.
* `data/egalites/` : deux arbres couvrants differents de meme cout (synthetique).
* `data/absorbants/` : circuits absorbants accessible et non accessible, avec les reponses attendues (couts artificiels).
* `data/tests_negatifs/` : petit circuit absorbant utilise par les tests de B.
* `data/petit/` : petit graphe synthetique de 8 sommets avec les resultats attendus calcules a la main.
* `data/realiste/` : ville synthetique de 120 sommets (Novapolis).
* `data/genere/` : jeu synthetique de 1000 sommets, regenerable avec la graine 42.
