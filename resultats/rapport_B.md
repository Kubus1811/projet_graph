## Section 3 : Accessibilité du réseau routier (Module 1)

### 3.1 Trois notions à ne pas confondre
Le réseau routier est un graphe **orienté** : à cause des sens uniques, aller de $u$ à $v$ ne garantit pas de pouvoir revenir. Nous utilisons trois notions distinctes, chacune pour un indicateur précis :

| Notion | Définition | Algorithme | Indicateur produit |
| :--- | :--- | :--- | :--- |
| **Accessibilité depuis une caserne** | $v$ est accessible s'il existe un chemin orienté d'une caserne vers $v$ | BFS multi-sources | Sites atteignables / non atteignables, caserne d'origine, part des sites sensibles atteints |
| **Connexité** (simple) | Le graphe est connexe si, en **oubliant le sens** des arcs, tous les sommets sont reliés | BFS sur le graphe symétrisé | Nombre de composantes connexes |
| **Connexité forte** | $u$ et $v$ sont dans la même composante si $u \to v$ **et** $v \to u$ | Kosaraju (2 DFS) | Nombre de CFC, sites hors de la grande CFC |

Les implications ne vont que dans un sens : fortement connexe ⇒ tout est accessible depuis n'importe quelle caserne ⇒ connexe. La réciproque est fausse. Sur le graphe `A → B → C → D` (test `test_accessible_mais_pas_fortement_connexe`), les sommets A à D sont accessibles depuis A et forment une seule composante connexe, mais chacun est sa propre CFC.

C'est l'accessibilité depuis les casernes qui compte pour les secours : un véhicule doit pouvoir **atteindre** le site. La connexité forte est un critère plus exigeant, qui répond à une autre question : le véhicule peut-il aussi **revenir** ?

### 3.2 Algorithmes implémentés (`src/parcours.py`)
Tous les parcours sont **itératifs** : la récursion Python est limitée vers 1000 appels, ce qui casserait sur le jeu généré (1000 sommets). Le test `test_dfs_pas_de_recursion_sur_long_graphe` vérifie ce point sur une chaîne de 5000 sommets. Les arcs au statut `ferme` sont ignorés. Les arcs `travaux` restent praticables.

| Fonction | Principe | Complexité |
| :--- | :--- | :--- |
| `dfs` | Version pile du cours : on dépile, on marque, on empile les successeurs | $O(\lvert V\rvert+\lvert E\rvert)$ |
| `bfs`, `chemin_min_arcs` | File FIFO + prédécesseurs : le chemin obtenu minimise le **nombre d'arcs** (pas la durée) | $O(\lvert V\rvert+\lvert E\rvert)$ |
| `accessibilite_multi_sources` | Toutes les casernes dans la file au départ ; chaque site hérite de la caserne qui l'a découvert | $O(\lvert V\rvert+\lvert E\rvert)$ |
| `trouver_circuit` | DFS à 3 couleurs : un arc vers un sommet **gris** (en cours de visite) ferme un circuit, qu'on reconstruit avec les parents | $O(\lvert V\rvert+\lvert E\rvert)$ |
| `sites_isoles`, `sites_non_atteignables` | Sommets sans arc entrant ni sortant / non atteints par le BFS multi-sources | $O(\lvert V\rvert+\lvert E\rvert)$ |
| `composantes_fortement_connexes` | Kosaraju : DFS pour l'ordre de fin, puis DFS sur le graphe inversé dans l'ordre décroissant | $O(\lvert V\rvert+\lvert E\rvert)$ |

### 3.3 Résultats

| Jeu | Sites | Arcs | Atteignables depuis les casernes | Sites sensibles atteints | Comp. connexes | CFC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Petit (référence) | 8 | 19 | 8 / 8 | 2 / 2 | 1 | 1 |
| Réaliste (synthétique) | 120 | 431 | 120 / 120 | 15 / 15 | 1 | 1 |
| Généré (graine 42) | 1000 | 3000 | 1000 / 1000 | 182 / 182 | 1 | **2** |

* **Petit jeu :** l'arc `Q2 → Q3` est un sens unique, mais le graphe reste fortement connexe grâce au retour `Q3 → H1 → Q1 → Q2`. Les distances en nombre d'arcs depuis C1 obtenues par BFS correspondent exactement aux valeurs calculées à la main (`resultats_attendus.json`).
* **Jeu généré :** tous les sites sont accessibles, mais le graphe n'est **pas** fortement connexe. Le site `S1000` n'a aucun arc sortant : un véhicule peut y aller mais pas en repartir par la route. Seule la connexité forte détecte ce cas ; l'accessibilité depuis les casernes ne le voit pas.
* Les deux jeux contiennent des circuits orientés (par exemple `CAS_01 → QUA_056 → HOP_01 → CAS_01`). C'est normal pour un réseau routier à double sens et sans incidence sur les plus courts chemins, puisque toutes les durées sont positives.

---

## Section 4 : Itinéraires des secours (Module 2)

### 4.1 Les trois algorithmes (`src/chemins.py`)
Les trois algorithmes renvoient le même format `(dist, pred)`, avec `dist[v] = inf` si $v$ est inaccessible et `-inf` si sa distance peut diminuer indéfiniment. Une seule fonction, `reconstruire_chemin`, sert donc aux trois.

| Algorithme | Mise en œuvre | Complexité | Quand l'utiliser |
| :--- | :--- | :--- | :--- |
| **Dijkstra** | Tas binaire `heapq`, suppression paresseuse (une entrée $(d,u)$ avec $d >$ `dist[u]` est périmée et ignorée). Refuse tout poids négatif avec un message nommant l'arc fautif | $O((\lvert V\rvert+\lvert E\rvert)\log\lvert V\rvert)$ | Cas métier : durées positives, une source ou plusieurs (casernes) |
| **Bellman–Ford** | $\lvert V\rvert-1$ passes de relâchement avec arrêt anticipé si une passe ne change rien, puis une passe de détection. Les sommets encore relâchables et tout ce qu'ils atteignent reçoivent `-inf` | $O(\lvert V\rvert\cdot\lvert E\rvert)$ | Poids négatifs possibles (module 3) |
| **Floyd–Warshall** | Matrice $L$ des distances et matrice $P$ des prédécesseurs ($P[i][j]$ = prédécesseur de $j$ sur le chemin depuis $i$). Un circuit absorbant se lit sur la diagonale ($L[k][k] < 0$) | $O(\lvert V\rvert^3)$ temps, $O(\lvert V\rvert^2)$ mémoire | Toutes les paires, petits graphes (≤ quelques centaines de sommets) |

**Pourquoi Dijkstra refuse les poids négatifs :** il fixe définitivement un sommet dès qu'il sort du tas. Un arc négatif découvert plus tard pourrait faire baisser sa distance, et le résultat serait faux sans aucun message d'erreur. Le test `test_dijkstra_refuse_poids_negatif` vérifie qu'on lève une erreur au lieu de renvoyer un résultat faux.

**Choix de la caserne (`itineraires_demandes`) :** au lieu de lancer un Dijkstra par caserne, nous lançons **un seul Dijkstra multi-sources** : toutes les casernes entrent dans le tas à distance 0. Chaque sommet hérite de la caserne d'origine de son prédécesseur. On obtient pour chaque site la caserne la plus proche et le chemin associé, pour le coût d'un seul Dijkstra.

Pour chaque itinéraire, `decrire_itineraire` renvoie : le chemin, la durée, le nombre d'arcs et les tronçons en `travaux` traversés.

### 4.2 Vérification et concordance des trois algorithmes
* Sur le petit jeu, les distances depuis C1 et C2 sont **identiques aux valeurs calculées à la main** pour les trois algorithmes. Quand deux chemins ont la même durée (par exemple C1 → Q2 vaut 7 min par E1 ou par Q1), le test vérifie que le chemin renvoyé est valide et qu'il a le bon coût, sans imposer lequel des deux.
* Le test automatique `comparer_algorithmes` vérifie que Dijkstra, Bellman–Ford et Floyd–Warshall donnent les mêmes distances pour **toutes les paires** du petit jeu, de 15 sources du jeu réaliste (et pour les 120 sources hors tests), du petit jeu en heure de pointe, et de 3 sources du jeu généré (sans Floyd–Warshall, trop coûteux à 1000 sommets). Aucune différence.
* Avec des poids négatifs (jeu `tests_negatifs`, circuit $S2 \to S3 \to S4 \to S2$ de coût $-1$) : Bellman–Ford depuis S1 renvoie bien `-inf` pour S2, S3 et S4, et ne donne jamais de distance finie fausse.

### 4.3 Effet des fermetures et perturbations
Chaque scénario est appliqué **sur une copie** du graphe (`appliquer_scenario`). `comparer_scenario` calcule, pour chaque demande : le coût avant et après, le retard absolu, le retard relatif $(\text{après} - \text{avant})/\text{avant}$, l'accessibilité, le nouveau chemin, et les arcs du chemin initial qui ont été fermés.

**Petit jeu, fermeture de `C1 → Q1` :**

| Demande | Site | Avant | Après | Retard | Retard relatif | Chemin après |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| D1 | Q1 | 4.0 | 10.0 | +6.0 | +150 % | C1 → E1 → Q2 → Q1 |
| D2 | Q3 | 5.0 | 5.0 | 0 | 0 % | C2 → Q4 → Q3 |
| D3 | E1 | 5.0 | 5.0 | 0 | 0 % | C1 → E1 |
| D4 | H1 | 7.0 | 13.0 | +6.0 | +86 % | C2 → Q4 → Q3 → H1 |

Le résultat de D1 correspond au calcul fait à la main (10 min, +150 %). Pour D4 (hôpital), la caserne C2 devient aussi rapide que C1 (13 min par les deux) : il faut un détour, mais aucune demande ne devient inaccessible.

**Synthèse des scénarios routiers :**

| Jeu | Scénario | Demandes retardées | Retard moyen\* | Retard max | Devenues inaccessibles |
| :--- | :--- | :---: | :---: | :---: | :---: |
| Petit | Fermeture `C1 → Q1` | 2 / 4 | 3.0 min | 6.0 min | 0 |
| Petit | Heure de pointe | 4 / 4 | 4.25 min | 7.0 min | 0 |
| Réaliste | `fermeture_pont_central` (CAS_01 ↔ HOP_01) | 0 / 25 | 0 | 0 | 0 |
| Réaliste | Fermeture `CAS_01 ↔ QUA_046` | 5 / 25 | 2.9 min | **29.0 min** | 0 |
| Réaliste | Heure de pointe | 25 / 25 | 21.3 min | 40.6 min | 0 |

\* Moyenne calculée sur toutes les demandes accessibles, retards nuls compris.

**Interprétation :**
* La fermeture du « pont central » du jeu réaliste **n'a aucun effet** sur les 25 demandes : aucun de leurs plus courts chemins ne passe par cet arc. Un axe n'est important que s'il est **effectivement utilisé** par les itinéraires. Pour trouver un axe vraiment critique, nous avons compté combien de chemins de demandes passent par chaque arc. `CAS_01 → QUA_046` est emprunté par 5 itinéraires : sa fermeture provoque jusqu'à 29 min de retard, sans pour autant rendre de site inaccessible.
* L'heure de pointe pénalise toutes les demandes (+21 min en moyenne, jusqu'à +122 % en relatif), mais ne change aucune affectation de caserne : la congestion ralentit tout le réseau à peu près uniformément.
* Les ralentissements ponctuels (`modifier_temps` sur Q1 → Q2 dans le petit jeu, CAS_04 → TEL_04 dans le jeu réaliste) n'ont aucun effet : ces arcs ne figuraient sur aucun plus court chemin, et des alternatives existaient.

### 4.4 Limites
* Les temps de parcours sont **fixes** : pas de congestion qui dépend du trafic, pas de temps de traversée des carrefours.
* La caserne retenue est la plus proche **en durée**. On ne tient compte ni de la disponibilité des véhicules, ni de la priorité des demandes, ni de plusieurs interventions en même temps.
* Un arc en `travaux` reste praticable avec son temps nominal, sauf si un scénario `modifier_temps` le ralentit.
* Floyd–Warshall n'est utilisable que sur de petits graphes : $n^3 = 10^9$ opérations pour $n = 1000$.
