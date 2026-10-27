# Résultats Attendus du Petit Graphe de Référence (8 sommets)

Ce document sert de **vérité terrain** (ground truth) pour les personnes B (parcours et chemins) et C (fibre, Kruskal/Prim, pannes).

---

## 1. Composition des sites
* `C1` : Caserne Centrale
* `C2` : Caserne Sud
* `H1` : Hôpital Nord
* `Q1` : Quartier République
* `Q2` : Quartier Bastille
* `Q3` : Quartier Nation
* `Q4` : Quartier Bercy
* `E1` : École Pasteur

---

## 2. Réseau Routier (Orienté) - Plus courts chemins (temps normal)

### Départs depuis C1 :
| Destination | Distance minimale | Chemin optimal |
| :--- | :--- | :--- |
| `C1` | **0.0 min** | `[C1]` |
| `Q1` | **4.0 min** | `[C1, Q1]` |
| `H1` | **7.0 min** | `[C1, Q1, H1]` |
| `E1` | **5.0 min** | `[C1, E1]` |
| `Q2` | **7.0 min** | `[C1, E1, Q2]` (ou `[C1, Q1, Q2]`) |
| `Q3` | **11.0 min** | `[C1, E1, Q2, Q3]` |
| `Q4` | **13.0 min** | `[C1, E1, Q2, Q3, Q4]` |
| `C2` | **11.0 min** | `[C1, E1, C2]` |

### Départs depuis C2 :
| Destination | Distance minimale | Chemin optimal |
| :--- | :--- | :--- |
| `C2` | **0.0 min** | `[C2]` |
| `Q4` | **3.0 min** | `[C2, Q4]` |
| `Q3` | **5.0 min** | `[C2, Q4, Q3]` |
| `E1` | **6.0 min** | `[C2, E1]` |
| `Q2` | **8.0 min** | `[C2, E1, Q2]` |
| `C1` | **11.0 min** | `[C2, E1, C1]` |
| `Q1` | **11.0 min** | `[C2, E1, Q2, Q1]` |
| `H1` | **13.0 min** | `[C2, Q4, Q3, H1]` |

---

## 3. Réseau de Fibre Optique (Non orienté) - Arbre Couvrant Minimal (ACM)

* **Nombre de sommets :** 8
* **Nombre d'arêtes nécessaires :** 7
* **Coût total minimal :** **35.0 unités**

### Arêtes sélectionnées dans l'ACM :
1. `(Q3, Q4)` - coût : 3.0
2. `(C1, E1)` - coût : 4.0
3. `(E1, Q2)` - coût : 4.0
4. `(C1, Q1)` - coût : 5.0
5. `(C2, Q4)` - coût : 5.0
6. `(H1, Q1)` - coût : 6.0
7. `(Q2, Q3)` - coût : 8.0

*(L'arête `Q1-Q2` de coût 7.0 forme un cycle avec `C1-E1-Q2-Q1` et est donc rejetée).*

---

## 4. Scénario de Panne Fibre (Arête `Q2-Q3`)

Si l'arête `(Q2, Q3)` de coût 8.0 tombe en panne :
* Le graphe est scindé en 2 composantes :
  * Composante Nord-Ouest : `{C1, E1, H1, Q1, Q2}`
  * Composante Sud-Est : `{C2, Q3, Q4}`
* Arêtes de secours disponibles dans le graphe initial reliant les deux composantes :
  * `(C2, E1)` : coût **9.0** *(la moins chère)*
  * `(H1, Q3)` : coût **15.0**
* **Meilleure reconnexion :** Ajout de l'arête `(C2, E1)` pour un coût de réparation de **9.0**.

---

## 5. Scénario Routier : Fermeture de l'axe `C1 -> Q1`

* Trajet initial `C1 -> Q1` : 4.0 min
* Après fermeture de l'arc direct `C1 -> Q1` :
  * Nouveau chemin optimal : `[C1, E1, Q2, Q1]`
  * Nouveau temps : $5.0 + 2.0 + 3.0 = 10.0$ min
  * **Retard absolu :** $+6.0$ min
  * **Retard relatif :** $+150\%$ ($1.5$)
