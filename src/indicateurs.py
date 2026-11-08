import csv
import heapq
from pathlib import Path
from src.arbres import analyser_panne
from src.graphe import Graphe


def appliquer_scenario(graphe, regles, nom_scenario=None):
    # on travaille toujours sur une copie pour pas casser le graphe de base
    g_copie = graphe.copie()

    for r in regles:
        sc_nom = r.get("scenario", "").strip()
        if nom_scenario is not None and sc_nom != nom_scenario:
            continue

        action = r.get("action", "").strip()
        u = r.get("u", "").strip()
        v = r.get("v", "").strip()
        valeur = r.get("valeur", "").strip()

        if action == "fermer_route":
            if u and v:
                g_copie.supprimer_arc(u, v)

        elif action == "fermer_fibre":
            if u and v:
                g_copie.supprimer_arc(u, v)

        elif action == "modifier_temps":
            if u and v and valeur:
                try:
                    nouveau_temps = float(valeur)
                    g_copie.modifier_poids_arc(u, v, nouveau_temps)
                except ValueError:
                    pass

        elif action == "heure_pointe":
            for s_id in g_copie.sommets():
                for arc_adj in g_copie._adj.get(s_id, []):
                    attrs = arc_adj.get("attributs", {})
                    if "temps_pointe" in attrs:
                        arc_adj["poids"] = float(attrs["temps_pointe"])

    return g_copie


def _dijkstra_interne(graphe, source):
    # dijkstra avec tas binaire pour tourner meme si chemins.py de B n'est pas encore pret
    dist = {s: float("inf") for s in graphe.sommets()}
    pred = {s: None for s in graphe.sommets()}

    if not graphe.a_sommet(source):
        return dist, pred

    dist[source] = 0.0
    file_prio = [(0.0, source)]

    while file_prio:
        d_u, u = heapq.heappop(file_prio)
        if d_u > dist[u]:
            continue

        for v, poids in graphe.successeurs(u):
            if dist[u] + poids < dist[v]:
                dist[v] = dist[u] + poids
                pred[v] = u
                heapq.heappush(file_prio, (dist[v], v))

    return dist, pred


def _composantes_connexes_interne(graphe):
    # parcours bfs pour trouver les composantes de la fibre
    vus = set()
    composantes = []

    for s in graphe.sommets():
        if s not in vus:
            comp = set()
            file = [s]
            vus.add(s)
            while file:
                courant = file.pop(0)
                comp.add(courant)
                for voisin, _ in graphe.successeurs(courant):
                    if voisin not in vus:
                        vus.add(voisin)
                        file.append(voisin)
            composantes.append(comp)
    return composantes


def evaluer_resilience_demandes(g_routes, casernes, demandes):
    # utilise chemins.py de B si dispo sinon notre dijkstra interne
    distances_par_caserne = {}
    for c in casernes:
        try:
            from src import chemins
            dist, _ = chemins.dijkstra(g_routes, c)
        except (ImportError, AttributeError):
            dist, _ = _dijkstra_interne(g_routes, c)
        distances_par_caserne[c] = dist

    total_demandes = len(demandes)
    inaccessibles = 0
    temps_totaux = []
    details = {}

    for d in demandes:
        d_id = d["id"]
        cible = d["origine"]
        meilleure_dist = float("inf")
        meilleure_caserne = None

        for c in casernes:
            d_val = distances_par_caserne[c].get(cible, float("inf"))
            if d_val < meilleure_dist:
                meilleure_dist = d_val
                meilleure_caserne = c

        if meilleure_dist == float("inf"):
            inaccessibles += 1
            details[d_id] = {"accessible": False, "temps": None, "caserne": None}
        else:
            temps_totaux.append(meilleure_dist)
            details[d_id] = {"accessible": True, "temps": meilleure_dist, "caserne": meilleure_caserne}

    temps_moyen = (sum(temps_totaux) / len(temps_totaux)) if temps_totaux else 0.0
    temps_max = max(temps_totaux) if temps_totaux else 0.0

    return {
        "total_demandes": total_demandes,
        "inaccessibles": inaccessibles,
        "temps_moyen": round(temps_moyen, 2),
        "temps_max": round(temps_max, 2),
        "details": details,
    }


def evaluer_resilience_fibre(g_fibre):
    try:
        from src import arbres
        composantes = arbres.trouver_composantes(g_fibre)
    except (ImportError, AttributeError):
        composantes = _composantes_connexes_interne(g_fibre)

    return {
        "nb_composantes": len(composantes),
        "est_connexe": len(composantes) <= 1,
    }


def evaluer_panne_fibre(g_fibre, regles, nom_scenario):
    pannes = [r for r in regles if r["action"] == "fermer_fibre" and r["scenario"] == nom_scenario]

    if len(pannes) > 1:
        raise ValueError(f"Scenario '{nom_scenario}' : plusieurs pannes simultanees non gerees.")

    if not pannes:
        return {
            "nb_composantes": evaluer_resilience_fibre(g_fibre)["nb_composantes"],
            "cout_reparation": 0.0,
        }

    res = analyser_panne(g_fibre, pannes[0]["u"], pannes[0]["v"])
    return {
        "nb_composantes": res["nb_composantes_panne"],
        # cout infini : aucun troncon disponible ne permet de reparer
        "cout_reparation": res["cout_reparation"] if res["raccordable"] else float("inf"),
    }


def bilan_routes(g_ref, g_scenario, demandes, casernes):
    # indicateurs routes fournis par B (chemins.py) : meme calcul partout dans le projet
    from src.chemins import comparer_scenario, indicateurs_routes

    lignes = comparer_scenario(g_ref, g_scenario, demandes, casernes)
    ind = indicateurs_routes(lignes, g_scenario, casernes)
    temps = [l["cout_apres"] for l in lignes if l["accessible_apres"]]
    return {
        "inaccessibles": ind["nb_inaccessibles_apres"],
        "temps_moyen": round(sum(temps) / len(temps), 2) if temps else 0.0,
        # moyenne sur toutes les demandes accessibles, retards nuls compris (definition de B)
        "retard_moyen": round(ind["retard_moyen"], 2),
        "retard_max": round(ind["retard_max"], 2),
        "sensibles": round(100 * ind["proportion_sensibles_accessibles"], 1),
    }


def orchestrer_module_5(donnees, dossier_resultats="resultats"):
    # calcule les 3 scenarios demandes : normal, axe ferme, panne fibre
    dossier = Path(dossier_resultats)
    dossier.mkdir(parents=True, exist_ok=True)

    g_routes_ref = donnees["graphe_routes"]
    g_fibre_ref = donnees["graphe_fibre"]
    sites = donnees["sites"]
    demandes = donnees["demandes"]
    regles = donnees.get("scenarios", [])

    casernes = [s_id for s_id, attr in sites.items() if attr.get("type") == "caserne"]
    if not casernes:
        casernes = [g_routes_ref.sommets()[0]] if g_routes_ref.sommets() else []

    # 1. scenario normal
    routes_s1 = bilan_routes(g_routes_ref, g_routes_ref, demandes, casernes)
    eval_fibre_s1 = evaluer_resilience_fibre(g_fibre_ref)

    # 2. fermeture d'un axe
    scen_route_nom = "fermeture_route_C1_Q1"
    for r in regles:
        if r["action"] == "fermer_route":
            scen_route_nom = r["scenario"]
            break

    g_routes_s2 = appliquer_scenario(g_routes_ref, regles, nom_scenario=scen_route_nom)
    routes_s2 = bilan_routes(g_routes_ref, g_routes_s2, demandes, casernes)
    eval_fibre_s2 = eval_fibre_s1

    # 3. panne fibre
    scen_fibre_nom = "panne_fibre_troncon_central"
    for r in regles:
        if r["action"] == "fermer_fibre":
            scen_fibre_nom = r["scenario"]
            break

    routes_s3 = routes_s1
    eval_fibre_s3 = evaluer_panne_fibre(g_fibre_ref, regles, scen_fibre_nom)

    tableau_comparatif = [
        {
            "Scénario": "1. Situation normale",
            "Demandes inaccessibles": routes_s1["inaccessibles"],
            "Temps moyen (min)": routes_s1["temps_moyen"],
            "Retard moyen (min)": routes_s1["retard_moyen"],
            "Retard max (min)": routes_s1["retard_max"],
            "Sites sensibles accessibles (%)": routes_s1["sensibles"],
            "Composantes Fibre": eval_fibre_s1["nb_composantes"],
            "Coût réparation fibre": 0.0,
        },
        {
            "Scénario": f"2. Fermeture axe ({scen_route_nom})",
            "Demandes inaccessibles": routes_s2["inaccessibles"],
            "Temps moyen (min)": routes_s2["temps_moyen"],
            "Retard moyen (min)": routes_s2["retard_moyen"],
            "Retard max (min)": routes_s2["retard_max"],
            "Sites sensibles accessibles (%)": routes_s2["sensibles"],
            "Composantes Fibre": eval_fibre_s2["nb_composantes"],
            "Coût réparation fibre": 0.0,
        },
        {
            "Scénario": f"3. Panne fibre ({scen_fibre_nom})",
            "Demandes inaccessibles": routes_s3["inaccessibles"],
            "Temps moyen (min)": routes_s3["temps_moyen"],
            "Retard moyen (min)": routes_s3["retard_moyen"],
            "Retard max (min)": routes_s3["retard_max"],
            "Sites sensibles accessibles (%)": routes_s3["sensibles"],
            "Composantes Fibre": eval_fibre_s3["nb_composantes"],
            "Coût réparation fibre": eval_fibre_s3["cout_reparation"],
        },
    ]

    lignes_md = [
        "# Synthese de Resilience - Module 5",
        "",
        "| Scenario | Demandes inaccessibles | Temps moyen (min) | Retard moyen (min) | Retard max (min) | Sites sensibles accessibles (%) | Composantes Fibre | Cout reparation |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for row in tableau_comparatif:
        lignes_md.append(
            f"| {row['Scénario']} | {row['Demandes inaccessibles']} | {row['Temps moyen (min)']} | "
            f"{row['Retard moyen (min)']} | {row['Retard max (min)']} | {row['Sites sensibles accessibles (%)']} | "
            f"{row['Composantes Fibre']} | {row['Coût réparation fibre']} |"
        )

    f_md = dossier / "tableau_resilience.md"
    f_md.write_text("\n".join(lignes_md), encoding="utf-8")

    f_csv = dossier / "tableau_resilience.csv"
    with open(f_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(tableau_comparatif[0].keys()))
        writer.writeheader()
        writer.writerows(tableau_comparatif)

    return {
        "tableau": tableau_comparatif,
        "fichier_md": str(f_md),
        "fichier_csv": str(f_csv),
    }
