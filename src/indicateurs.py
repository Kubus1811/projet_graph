import csv
import re
from pathlib import Path
from src.arbres import reparer_pannes, trouver_composantes


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

        # routes et fibre partagent les memes sites : chaque action ne vise que son reseau
        if action == "fermer_route":
            if g_copie.oriente and u and v:
                g_copie.supprimer_arc(u, v)

        elif action == "fermer_fibre":
            if not g_copie.oriente and u and v:
                g_copie.supprimer_arc(u, v)

        elif action == "modifier_temps":
            if g_copie.oriente and u and v and valeur:
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


def verifier_scenario(regles, nom_scenario):
    # sans ce controle une faute de frappe donnerait un faux resultat "sans effet"
    noms = sorted({r["scenario"] for r in regles})
    if nom_scenario not in noms:
        raise ValueError(f"Scenario '{nom_scenario}' inconnu. Scenarios disponibles : {', '.join(noms) or 'aucun'}.")


def evaluer_resilience_fibre(g_fibre):
    composantes = trouver_composantes(g_fibre)

    return {
        "nb_composantes": len(composantes),
        "est_connexe": len(composantes) <= 1,
    }


def evaluer_panne_fibre(g_fibre, regles, nom_scenario):
    pannes = [(r["u"], r["v"]) for r in regles if r["action"] == "fermer_fibre" and r["scenario"] == nom_scenario]

    if not pannes:
        return {
            "nb_composantes": evaluer_resilience_fibre(g_fibre)["nb_composantes"],
            "cout_reparation": 0.0,
        }

    res = reparer_pannes(g_fibre, pannes)
    return {
        "nb_composantes": res["nb_composantes_panne"],
        # cout infini : aucun troncon disponible ne permet de tout reconnecter
        "cout_reparation": res["cout_reparation"] if res["nb_composantes_apres"] == res["nb_composantes_avant"] else float("inf"),
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


def _ligne_tableau(libelle, routes, nb_composantes, cout_reparation):
    return {
        "Scénario": libelle,
        "Demandes inaccessibles": routes["inaccessibles"],
        "Temps moyen (min)": routes["temps_moyen"],
        "Retard moyen (min)": routes["retard_moyen"],
        "Retard max (min)": routes["retard_max"],
        "Sites sensibles accessibles (%)": routes["sensibles"],
        "Composantes Fibre": nb_composantes,
        "Coût réparation fibre": cout_reparation,
    }


def _nom_fichier_tableau(nom_jeu, nom_scenario):
    nom = "_".join(m for m in ("tableau_resilience", nom_jeu, nom_scenario) if m)
    # le nom du scenario vient d'un csv : pas de separateur de chemin dans le fichier
    return re.sub(r"[^\w-]", "_", nom)


def orchestrer_module_5(donnees, dossier_resultats="resultats", nom_jeu=None, nom_scenario=None):
    # sans scenario : les 3 scenarios demandes (normal, axe ferme, panne fibre)
    # avec un scenario : la situation normale comparee a ce scenario
    if nom_scenario is not None:
        verifier_scenario(donnees.get("scenarios", []), nom_scenario)

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
    composantes_s1 = evaluer_resilience_fibre(g_fibre_ref)["nb_composantes"]
    tableau_comparatif = [_ligne_tableau("1. Situation normale", routes_s1, composantes_s1, 0.0)]

    if nom_scenario is not None:
        g_routes = appliquer_scenario(g_routes_ref, regles, nom_scenario=nom_scenario)
        fibre = evaluer_panne_fibre(g_fibre_ref, regles, nom_scenario)
        tableau_comparatif.append(_ligne_tableau(
            f"2. Scenario ({nom_scenario})",
            bilan_routes(g_routes_ref, g_routes, demandes, casernes),
            fibre["nb_composantes"],
            fibre["cout_reparation"],
        ))
    else:
        # 2. fermeture d'un axe
        scen_route_nom = "fermeture_route_C1_Q1"
        for r in regles:
            if r["action"] == "fermer_route":
                scen_route_nom = r["scenario"]
                break

        g_routes_s2 = appliquer_scenario(g_routes_ref, regles, nom_scenario=scen_route_nom)
        routes_s2 = bilan_routes(g_routes_ref, g_routes_s2, demandes, casernes)
        tableau_comparatif.append(_ligne_tableau(f"2. Fermeture axe ({scen_route_nom})", routes_s2, composantes_s1, 0.0))

        # 3. panne fibre
        scen_fibre_nom = "panne_fibre_troncon_central"
        for r in regles:
            if r["action"] == "fermer_fibre":
                scen_fibre_nom = r["scenario"]
                break

        fibre_s3 = evaluer_panne_fibre(g_fibre_ref, regles, scen_fibre_nom)
        tableau_comparatif.append(_ligne_tableau(
            f"3. Panne fibre ({scen_fibre_nom})", routes_s1, fibre_s3["nb_composantes"], fibre_s3["cout_reparation"],
        ))

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

    # un fichier par jeu : sinon chaque execution ecrase le resultat du jeu precedent
    nom_fichier = _nom_fichier_tableau(nom_jeu, nom_scenario)
    f_md = dossier / f"{nom_fichier}.md"
    f_md.write_text("\n".join(lignes_md), encoding="utf-8")

    f_csv = dossier / f"{nom_fichier}.csv"
    with open(f_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(tableau_comparatif[0].keys()))
        writer.writeheader()
        writer.writerows(tableau_comparatif)

    return {
        "tableau": tableau_comparatif,
        "fichier_md": str(f_md),
        "fichier_csv": str(f_csv),
    }
