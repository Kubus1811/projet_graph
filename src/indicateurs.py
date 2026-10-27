import csv
import heapq
from pathlib import Path
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
    eval_routes_s1 = evaluer_resilience_demandes(g_routes_ref, casernes, demandes)
    eval_fibre_s1 = evaluer_resilience_fibre(g_fibre_ref)

    # 2. fermeture d'un axe
    scen_route_nom = "fermeture_route_C1_Q1"
    for r in regles:
        if r["action"] == "fermer_route":
            scen_route_nom = r["scenario"]
            break

    g_routes_s2 = appliquer_scenario(g_routes_ref, regles, nom_scenario=scen_route_nom)
    eval_routes_s2 = evaluer_resilience_demandes(g_routes_s2, casernes, demandes)
    eval_fibre_s2 = eval_fibre_s1

    retards = []
    for d_id, det_s1 in eval_routes_s1["details"].items():
        det_s2 = eval_routes_s2["details"].get(d_id, {})
        if det_s1["accessible"] and det_s2.get("accessible"):
            t1 = det_s1["temps"]
            t2 = det_s2["temps"]
            if t2 > t1:
                retards.append(t2 - t1)

    retard_moyen = (sum(retards) / len(retards)) if retards else 0.0
    retard_max = max(retards) if retards else 0.0

    # 3. panne fibre
    scen_fibre_nom = "panne_fibre_troncon_central"
    for r in regles:
        if r["action"] == "fermer_fibre":
            scen_fibre_nom = r["scenario"]
            break

    g_fibre_s3 = appliquer_scenario(g_fibre_ref, regles, nom_scenario=scen_fibre_nom)
    eval_routes_s3 = eval_routes_s1
    eval_fibre_s3 = evaluer_resilience_fibre(g_fibre_s3)

    cout_reconnexion = 0.0
    if eval_fibre_s3["nb_composantes"] > eval_fibre_s1["nb_composantes"]:
        cout_reconnexion = 9.0

    tableau_comparatif = [
        {
            "Scénario": "1. Situation normale",
            "Demandes inaccessibles": eval_routes_s1["inaccessibles"],
            "Temps moyen (min)": eval_routes_s1["temps_moyen"],
            "Retard moyen (min)": 0.0,
            "Retard max (min)": 0.0,
            "Composantes Fibre": eval_fibre_s1["nb_composantes"],
            "Coût réparation fibre": 0.0,
        },
        {
            "Scénario": f"2. Fermeture axe ({scen_route_nom})",
            "Demandes inaccessibles": eval_routes_s2["inaccessibles"],
            "Temps moyen (min)": eval_routes_s2["temps_moyen"],
            "Retard moyen (min)": round(retard_moyen, 2),
            "Retard max (min)": round(retard_max, 2),
            "Composantes Fibre": eval_fibre_s2["nb_composantes"],
            "Coût réparation fibre": 0.0,
        },
        {
            "Scénario": f"3. Panne fibre ({scen_fibre_nom})",
            "Demandes inaccessibles": eval_routes_s3["inaccessibles"],
            "Temps moyen (min)": eval_routes_s3["temps_moyen"],
            "Retard moyen (min)": 0.0,
            "Retard max (min)": 0.0,
            "Composantes Fibre": eval_fibre_s3["nb_composantes"],
            "Coût réparation fibre": cout_reconnexion,
        },
    ]

    lignes_md = [
        "# Synthese de Resilience - Module 5",
        "",
        "| Scenario | Demandes inaccessibles | Temps moyen (min) | Retard moyen (min) | Retard max (min) | Composantes Fibre | Cout reparation |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for row in tableau_comparatif:
        lignes_md.append(
            f"| {row['Scénario']} | {row['Demandes inaccessibles']} | {row['Temps moyen (min)']} | "
            f"{row['Retard moyen (min)']} | {row['Retard max (min)']} | {row['Composantes Fibre']} | {row['Coût réparation fibre']} |"
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
