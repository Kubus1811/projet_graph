# Jeu de données Réaliste - Novapolis (SYNTHÉTIQUE)

> [!NOTE]
> **Statut des données : SYNTHÉTIQUE**
> Ce jeu de données a été généré de manière procédurale pour modéliser une métropole réaliste de 120 sites, articulée autour de 4 zones urbaines (Centre, Zone Maritime Sud, Colline Nord, Quartier d'Affaires Est) et traversée par un fleuve équipé de 3 ponts stratégiques.

## Contenu :
* `sites.csv` : 120 sites (4 casernes `CAS_01` à `CAS_04`, 3 hôpitaux `HOP_01` à `HOP_03`, 4 centres télécoms `TEL_01` à `TEL_04`, 8 écoles `ECO_01` à `ECO_08`, 101 quartiers `QUA_001` à `QUA_101`).
* `routes.csv` : 431 arcs routiers pondérés en minutes (temps normal et temps de pointe), sens uniques et double sens.
* `fibre.csv` : 163 tronçons de fibre optique non orientés avec coûts de génie civil.
* `demandes.csv` : 25 demandes d'interventions réparties (incendie, accident, urgence médicale, fuite de gaz).
* `scenarios.csv` : Scénarios documentés dont la fermeture du pont central et l'heure de pointe générale.
