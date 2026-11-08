import csv
from functools import lru_cache
from pathlib import Path

from src import chemins
from src.arbres import kruskal, reparer_pannes
from src.indicateurs import appliquer_scenario
from src.io_donnees import charger_jeu_donnees
from src.parcours import arc_ouvert

DOSSIER_DATA = Path(__file__).resolve().parent.parent / "data"

# liste fermee : le nom recu du navigateur ne sert jamais a construire un chemin libre
JEUX = {
    "petit": "Petit graphe (8 sites, vérifiable à la main)",
    "realiste": "Novapolis (120 sites, données synthétiques)",
}
TYPES_SENSIBLES = {"hopital", "ecole", "telecom"}


def _fibre_disponible(attributs):
    # fibre : un troncon en travaux ou ferme est indisponible (zone de travaux du sujet)
    return attributs.get("statut", "ouvert") == "ouvert"


def _sans_troncons_indisponibles(graphe, est_disponible):
    g = graphe.copie()
    for u, v, _ in graphe.arcs():
        if not est_disponible(graphe.attributs_arc(u, v)):
            g.supprimer_arc(u, v)
    return g


def preparer_jeu(donnees):
    # routes : meme regle que parcours.py (B), une route en travaux reste praticable, une route fermee non
    routes = _sans_troncons_indisponibles(donnees["graphe_routes"], arc_ouvert)
    fibre = _sans_troncons_indisponibles(donnees["graphe_fibre"], _fibre_disponible)
    casernes = [s for s, a in donnees["sites"].items() if a["type"] == "caserne"]
    return {**donnees, "routes": routes, "fibre": fibre, "casernes": casernes}


@lru_cache(maxsize=None)
def _charger(nom):
    if nom not in JEUX:
        raise ValueError(f"Jeu de donnees inconnu : '{nom}'.")
    return preparer_jeu(charger_jeu_donnees(DOSSIER_DATA / nom))


def moteur_itineraires():
    return "Dijkstra multi-sources de chemins.py (partie B)"


def _itineraires(graphe, jeu):
    # partie B : une seule recherche depuis toutes les casernes, chaque demande prend la plus proche
    its = chemins.itineraires_demandes(graphe, jeu["demandes"], jeu["casernes"])
    return {
        it["demande"]: {
            "accessible": it["accessible"],
            "temps": it["duree"] if it["accessible"] else None,
            "caserne": it["caserne"],
            "chemin": it["chemin"],
        }
        for it in its
    }


def _reseau_perturbe(routes, routes_fermees=(), temps_modifies=(), pointe=False):
    # toujours une copie : le scenario de reference ne change jamais
    g = routes.copie()
    if pointe:
        regle = {"scenario": "pointe", "action": "heure_pointe", "u": "", "v": "", "valeur": ""}
        g = appliquer_scenario(g, [regle], nom_scenario="pointe")
    for u, v, temps in temps_modifies:
        if not g.a_arc(u, v):
            raise ValueError(f"La route {u} -> {v} n'existe pas.")
        g.modifier_poids_arc(u, v, float(temps))
    for u, v in routes_fermees:
        if not g.a_arc(u, v):
            raise ValueError(f"La route {u} -> {v} n'existe pas.")
        g.supprimer_arc(u, v)
    return g


def _ligne_demande(demande, ligne_b):
    # une ligne de comparer_scenario (B), au format attendu par le site
    avant = ligne_b["cout_avant"] if ligne_b["accessible_avant"] else None
    relatif = ligne_b["retard_relatif"]
    chemin = ligne_b["chemin_apres"]
    return {
        **demande,
        "accessible": ligne_b["accessible_apres"],
        "temps_avant": avant,
        "temps_apres": ligne_b["cout_apres"] if ligne_b["accessible_apres"] else None,
        "retard": ligne_b["retard_absolu"],
        # une demande sur la caserne meme a un temps nul : pas de retard relatif
        "retard_relatif": relatif if avant else None,
        "caserne_avant": ligne_b["caserne_avant"],
        "caserne": ligne_b["caserne_apres"],
        "chemin_avant": ligne_b["chemin_avant"],
        "chemin": chemin,
        "nb_arcs": len(chemin) - 1 if chemin else None,
    }


def simuler(nom, routes_fermees=(), fibres_en_panne=(), temps_modifies=(), pointe=False):
    jeu = _charger(nom)
    g = _reseau_perturbe(jeu["routes"], routes_fermees, temps_modifies, pointe)

    # avant / apres et indicateurs routes : fonctions de la partie B
    lignes_b = chemins.comparer_scenario(jeu["routes"], g, jeu["demandes"], jeu["casernes"])
    ind = chemins.indicateurs_routes(lignes_b, g, jeu["casernes"])
    par_id = {d["id"]: d for d in jeu["demandes"]}
    lignes = [_ligne_demande(par_id[l["demande"]], l) for l in lignes_b]

    # temps de reponse de chaque site : dijkstra multi-sources de B
    dist, _, _ = chemins.dijkstra_multi_sources(g, jeu["casernes"])
    fibre = reparer_pannes(jeu["fibre"], fibres_en_panne)

    return {
        "temps_sites": {s: _fini(dist.get(s, float("inf"))) for s in jeu["sites"]},
        "demandes": lignes,
        "indicateurs": {
            "inaccessibles": ind["nb_inaccessibles_apres"],
            "total_demandes": ind["nb_demandes"],
            "retard_moyen": ind["retard_moyen"],
            "retard_max": ind["retard_max"],
            "part_sites_sensibles": ind["proportion_sensibles_accessibles"],
            "composantes_fibre": fibre["nb_composantes_panne"],
            "composantes_fibre_apres_reparation": fibre["nb_composantes_apres"],
            "cout_reparation": fibre["cout_reparation"],
            "cout_arbre": fibre["cout_arbre_apres"],
        },
        "fibre": fibre,
        "moteur": moteur_itineraires(),
    }


def _scenarios_du_jeu(regles):
    scenarios = {}
    for r in regles:
        s = scenarios.setdefault(r["scenario"], {
            "nom": r["scenario"],
            "routes_fermees": [],
            "fibres_en_panne": [],
            "temps_modifies": [],
            "pointe": False,
        })
        if r["action"] == "fermer_route":
            s["routes_fermees"].append([r["u"], r["v"]])
        elif r["action"] == "fermer_fibre":
            s["fibres_en_panne"].append([r["u"], r["v"]])
        elif r["action"] == "modifier_temps":
            s["temps_modifies"].append([r["u"], r["v"], float(r["valeur"])])
        elif r["action"] == "heure_pointe":
            s["pointe"] = True
    return list(scenarios.values())


def carte(nom):
    jeu = _charger(nom)
    return {
        "jeu": nom,
        "sites": [{"id": s, **a} for s, a in jeu["sites"].items()],
        "routes": [
            {
                "u": u,
                "v": v,
                "temps_normal": temps,
                "temps_pointe": jeu["routes"].attributs_arc(u, v).get("temps_pointe", temps),
            }
            for u, v, temps in jeu["routes"].arcs()
        ],
        "fibre": [
            {"u": min(u, v), "v": max(u, v), "cout": cout}
            for u, v, cout in jeu["fibre"].arcs()
        ],
        "scenarios": _scenarios_du_jeu(jeu["scenarios"]),
    }


def _axes_utilises(itineraires, routes):
    axes = set()
    for it in itineraires.values():
        chemin = it["chemin"] or []
        for u, v in zip(chemin, chemin[1:]):
            axes.add((min(u, v), max(u, v)))
    return sorted(axes)


def points_faibles(nom, limite=5):
    return points_faibles_du_jeu(_charger(nom), limite)


def points_faibles_du_jeu(jeu, limite=5):
    # test de resistance : on coupe chaque troncon un par un et on classe les degats
    routes = jeu["routes"]
    reference = _itineraires(routes, jeu)

    # couper une route qu'aucun itineraire n'emprunte ne peut retarder personne
    impacts_routes = []
    for a, b in _axes_utilises(reference, routes):
        fermes = [(u, v) for u, v in ((a, b), (b, a)) if routes.a_arc(u, v)]
        g = _reseau_perturbe(routes, fermes)
        apres = _itineraires(g, jeu)

        inaccessibles = 0
        retard_total = 0.0
        retard_max = 0.0
        touchees = 0
        for d_id, it in apres.items():
            if not it["accessible"]:
                inaccessibles += 1
            elif it["temps"] > reference[d_id]["temps"]:
                retard = it["temps"] - reference[d_id]["temps"]
                retard_total += retard
                retard_max = max(retard_max, retard)
                touchees += 1

        if inaccessibles or retard_total:
            impacts_routes.append({
                "u": a,
                "v": b,
                "routes_fermees": [list(f) for f in fermes],
                "inaccessibles": inaccessibles,
                "demandes_retardees": touchees,
                "retard_total": retard_total,
                "retard_max": retard_max,
            })
    impacts_routes.sort(key=lambda i: (-i["inaccessibles"], -i["retard_total"], i["u"], i["v"]))

    impacts_fibre = []
    for u, v, cout in kruskal(jeu["fibre"])["aretes"]:
        res = reparer_pannes(jeu["fibre"], [(u, v)])
        raccordable = bool(res["raccordements"])
        impacts_fibre.append({
            "u": u,
            "v": v,
            "cout": cout,
            "raccordable": raccordable,
            "cout_reparation": res["cout_reparation"],
            "surcout": res["cout_arbre_apres"] - res["cout_arbre_avant"] if raccordable else None,
        })
    # les troncons sans secours d'abord, puis ceux dont la reparation coute le plus cher
    impacts_fibre.sort(key=lambda i: (i["raccordable"], -(i["surcout"] or 0), i["u"], i["v"]))

    return {
        "routes": impacts_routes[:limite],
        "fibre": impacts_fibre[:limite],
        # classement complet pour colorer toute la carte des fragilites
        "routes_toutes": impacts_routes,
        "fibre_toutes": impacts_fibre,
        "nb_axes_testes": len(_axes_utilises(reference, routes)),
        "nb_troncons_testes": len(impacts_fibre),
    }


def comparer_reouvertures(jeu, axes):
    # tous les axes sont coupes sauf celui qu'on rouvre : quel choix laisse le moins de retard ?
    resultats = []
    for choisi in axes:
        fermes = [f for a in axes if a is not choisi for f in a["routes_fermees"]]
        g = _reseau_perturbe(jeu["routes"], fermes)
        lignes = chemins.comparer_scenario(jeu["routes"], g, jeu["demandes"], jeu["casernes"])
        resultats.append({
            "u": choisi["u"],
            "v": choisi["v"],
            "inaccessibles": sum(1 for l in lignes if not l["accessible_apres"]),
            "retard_restant": sum(l["retard_absolu"] or 0 for l in lignes),
        })
    return sorted(resultats, key=lambda r: (r["inaccessibles"], r["retard_restant"]))


def formater_points_faibles(res, reouvertures):
    lignes = [
        f"Axes routiers testes : {res['nb_axes_testes']}, troncons de fibre testes : {res['nb_troncons_testes']}",
        "",
        "--- Routes les plus critiques (coupees une par une) ---",
        f"{'Route':<26} {'Inacc.':>6} {'Retardees':>9} {'Retard cumule':>13} {'Retard max':>10}",
    ]
    for r in res["routes"]:
        route = f"{r['u']} <-> {r['v']}"
        lignes.append(f"{route:<26} {r['inaccessibles']:>6} {r['demandes_retardees']:>9} "
                      f"{r['retard_total']:>13.1f} {r['retard_max']:>10.1f}")

    lignes += ["", "--- Troncons de fibre les plus fragiles ---"]
    for t in res["fibre"]:
        detail = f"reparation {t['cout_reparation']:.1f}, surcout {t['surcout']:.1f}" if t["raccordable"] else "aucun raccordement possible"
        lignes.append(f"{t['u']} - {t['v']} (cout {t['cout']:.1f}) : {detail}")

    if reouvertures:
        lignes += ["", f"--- {len(reouvertures)} routes coupees en meme temps : laquelle rouvrir ? ---"]
        for r in reouvertures:
            lignes.append(f"Rouvrir {r['u']} <-> {r['v']} : retard cumule restant {r['retard_restant']:.1f} min, "
                          f"{r['inaccessibles']} demande(s) inaccessible(s)")
    return "\n".join(lignes)


def ecrire_points_faibles(res, nom_jeu, dossier_resultats="resultats"):
    dossier = Path(dossier_resultats)
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = dossier / f"points_faibles_{nom_jeu}.csv"
    champs = ["reseau", "u", "v", "inaccessibles", "demandes_retardees", "retard_total", "retard_max",
              "cout", "raccordable", "cout_reparation", "surcout"]

    def ligne(reseau, impact):
        return {"reseau": reseau, **{k: round(x, 2) if isinstance(x, float) else x for k, x in impact.items()}}

    with open(fichier, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=champs, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(ligne("route", r) for r in res["routes_toutes"])
        writer.writerows(ligne("fibre", t) for t in res["fibre_toutes"])
    return str(fichier)


# ---------------------------------------------------------------- visualisation de B integree au site

ALGORITHMES_CHEMIN = ("dijkstra", "bellman_ford", "floyd_warshall")
TAILLE_MAX_FLOYD = 400


def _fini(x):
    # le json ne connait pas l'infini : None veut dire inaccessible
    return None if x in (float("inf"), float("-inf")) else x


def _distances(g, algo, source):
    if algo == "dijkstra":
        return chemins.dijkstra(g, source)
    if algo == "bellman_ford":
        return chemins.bellman_ford(g, source)
    if algo == "floyd_warshall":
        if g.nombre_sommets() > TAILLE_MAX_FLOYD:
            raise ValueError(f"Floyd-Warshall est limite a {TAILLE_MAX_FLOYD} sommets (O(n^3)).")
        dist, pred = chemins.floyd_warshall(g)
        return dist[source], pred[source]
    raise ValueError(f"Algorithme inconnu : '{algo}'.")


def itineraire_interactif(nom, source, cible=None, algo="dijkstra", routes_fermees=(), temps_modifies=(), pointe=False):
    # meme calcul que la fenetre pygame de B, renvoye au site
    jeu = _charger(nom)
    source = str(source)
    if not jeu["routes"].a_sommet(source):
        raise ValueError(f"Site de depart inconnu : '{source}'.")
    if cible is not None and not jeu["routes"].a_sommet(str(cible)):
        raise ValueError(f"Site d'arrivee inconnu : '{cible}'.")

    g = _reseau_perturbe(jeu["routes"], routes_fermees, temps_modifies, pointe)
    dist, pred = _distances(g, algo, source)

    # ordre d'exploration : distances croissantes, c'est l'ordre ou dijkstra fixe les sommets
    atteints = sorted((s for s, d in dist.items() if d not in (float("inf"), float("-inf"))), key=lambda s: (dist[s], s))
    resultat = {
        "algo": algo,
        "source": source,
        "cible": None if cible is None else str(cible),
        "exploration": [[s, pred.get(s)] for s in atteints],
        "itineraire": None,
    }

    if cible is not None:
        it = chemins.decrire_itineraire(g, dist, pred, source, str(cible))
        chemin = it["chemin"]
        reference, _ = chemins.dijkstra(jeu["routes"], source)
        duree_ref = reference.get(str(cible), float("inf"))
        # les trois algorithmes de B doivent donner la meme duree
        comparaison = {}
        for a in ALGORITHMES_CHEMIN:
            if a == "floyd_warshall" and g.nombre_sommets() > TAILLE_MAX_FLOYD:
                continue
            d_a, _ = _distances(g, a, source)
            comparaison[a] = _fini(d_a.get(str(cible), float("inf")))
        resultat["itineraire"] = {
            "accessible": it["accessible"],
            "chemin": chemin,
            "duree": _fini(it["duree"]),
            "nb_arcs": it["nb_arcs"],
            "poids": [g.poids_arc(u, v) for u, v in zip(chemin, chemin[1:])] if chemin else [],
            "duree_reference": _fini(duree_ref),
            "travaux": [list(f) for f in it["fermetures"]],
            "comparaison": comparaison,
        }
    return resultat


def analyse_connexite(nom, routes_fermees=(), temps_modifies=(), pointe=False):
    # module 1 de B : accessibilite depuis les casernes, connexite et connexite forte
    from src.parcours import diagnostic_accessibilite

    jeu = _charger(nom)
    g = _reseau_perturbe(jeu["routes"], routes_fermees, temps_modifies, pointe)
    diag = diagnostic_accessibilite(g, jeu["casernes"])
    cfc = sorted(diag["cfc"], key=lambda c: (-len(c), c[0]))
    return {
        "casernes": diag["casernes"],
        "caserne_par_site": diag["caserne_par_site"],
        "non_atteignables": diag["non_atteignables"],
        "isoles": diag["isoles"],
        "sensibles_total": diag["sensibles_total"],
        "sensibles_accessibles": diag["sensibles_accessibles"],
        "nb_composantes_connexes": diag["nb_composantes_connexes"],
        "cfc": cfc,
        "circuit_exemple": diag["circuit_exemple"],
    }
