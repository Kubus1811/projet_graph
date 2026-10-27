import math
import random
from pathlib import Path
from src.io_donnees import (
    sauvegarder_sites,
    sauvegarder_routes,
    sauvegarder_fibre,
    sauvegarder_demandes,
    sauvegarder_scenarios,
)


def construire_jeu_realiste(dossier_sortie="data/realiste"):
    dossier = Path(dossier_sortie)
    dossier.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20261027)

    # 120 sites : casernes, hopitaux, telecom, ecoles, quartiers
    sites = {}

    def ajouter(s_id, nom, t, x, y):
        lon = round(2.30 + (x / 100.0) * 0.16, 6)
        lat = round(48.80 + (y / 100.0) * 0.16, 6)
        sites[s_id] = {
            "nom": nom,
            "type": t,
            "longitude": lon,
            "latitude": lat,
            "_x": x,
            "_y": y,
        }

    ajouter("CAS_01", "Caserne 1 - Centre", "caserne", 48.0, 52.0)
    ajouter("CAS_02", "Caserne 2 - Port Sud", "caserne", 25.0, 20.0)
    ajouter("CAS_03", "Caserne 3 - Colline Nord", "caserne", 75.0, 85.0)
    ajouter("CAS_04", "Caserne 4 - Parc Est", "caserne", 80.0, 40.0)

    ajouter("HOP_01", "CHU Novapolis Centre", "hopital", 52.0, 50.0)
    ajouter("HOP_02", "Hopital Sud Maritime", "hopital", 30.0, 15.0)
    ajouter("HOP_03", "Clinique Nord Pasteur", "hopital", 70.0, 80.0)

    ajouter("TEL_01", "Hub Telecom Central", "telecom", 50.0, 48.0)
    ajouter("TEL_02", "Datacenter Sud Industrie", "telecom", 20.0, 25.0)
    ajouter("TEL_03", "Noeud Telecom Nord", "telecom", 72.0, 78.0)
    ajouter("TEL_04", "Centre Technique Est", "telecom", 85.0, 42.0)

    for i in range(1, 9):
        sx = round(15.0 + (i * 10.5), 1)
        sy = round(20.0 + ((i % 4) * 20.0), 1)
        ajouter(f"ECO_0{i}", f"Groupe Scolaire {i}", "ecole", sx, sy)

    q_idx = 1
    for gx in range(10):
        for gy in range(10):
            if q_idx > 101:
                break
            s_id = f"QUA_{str(q_idx).zfill(3)}"
            base_x = 10.0 + gx * 8.5 + rng.uniform(-1.5, 1.5)
            base_y = 10.0 + gy * 8.5 + rng.uniform(-1.5, 1.5)
            ajouter(s_id, f"Quartier Q{q_idx}", "quartier", round(base_x, 1), round(base_y, 1))
            q_idx += 1

    if q_idx == 101:
        ajouter("QUA_101", "Esplanade des Fetes", "quartier", 50.0, 95.0)

    all_ids = list(sites.keys())

    # reseau routier
    routes = []
    routes_set = set()

    def ajouter_route(u, v, t_norm, t_pte, double_sens=True, statut="ouvert"):
        if (u, v) not in routes_set:
            routes_set.add((u, v))
            routes.append({
                "u": u, "v": v,
                "temps_normal": round(t_norm, 1),
                "temps_pointe": round(t_pte, 1),
                "statut": statut,
            })
        if double_sens and (v, u) not in routes_set:
            routes_set.add((v, u))
            routes.append({
                "u": v, "v": u,
                "temps_normal": round(t_norm, 1),
                "temps_pointe": round(t_pte, 1),
                "statut": statut,
            })

    # connexions selon la proximite et fleuve a y=50
    for u_id in all_ids:
        ux, uy = sites[u_id]["_x"], sites[u_id]["_y"]
        voisins = sorted(
            [v for v in all_ids if v != u_id],
            key=lambda v: math.hypot(ux - sites[v]["_x"], uy - sites[v]["_y"])
        )
        for v_id in voisins[:3]:
            vx, vy = sites[v_id]["_x"], sites[v_id]["_y"]
            dist = math.hypot(ux - vx, uy - vy)
            traverse_fleuve = (uy < 49.0 and vy > 51.0) or (uy > 51.0 and vy < 49.0)
            if traverse_fleuve and not (40.0 <= ux <= 60.0 or ux <= 32.0 or ux >= 70.0):
                continue

            vitesse = 0.8 if dist < 10 else 1.2
            t_norm = max(1.0, dist * vitesse + rng.uniform(0.2, 1.0))
            t_pte = t_norm * rng.uniform(1.4, 2.3)
            est_double = rng.random() < 0.85
            ajouter_route(u_id, v_id, t_norm, t_pte, double_sens=est_double)

    for cas in ["CAS_01", "CAS_02", "CAS_03", "CAS_04"]:
        for hop in ["HOP_01", "HOP_02", "HOP_03"]:
            dist = math.hypot(sites[cas]["_x"] - sites[hop]["_x"], sites[cas]["_y"] - sites[hop]["_y"])
            if dist < 30.0:
                t_norm = round(dist * 0.9, 1)
                ajouter_route(cas, hop, t_norm, round(t_norm * 1.5, 1), double_sens=True)

    # pont central strategique
    ajouter_route("CAS_01", "HOP_01", 3.0, 8.0, double_sens=True)
    ajouter_route("CAS_01", "QUA_050", 4.0, 9.5, double_sens=True)

    # reseau fibre non oriente
    fibre = []
    fibre_set = set()

    def ajouter_fibre(u, v, cost, statut="ouvert"):
        cle = (u, v) if u <= v else (v, u)
        if cle not in fibre_set:
            fibre_set.add(cle)
            fibre.append({
                "u": cle[0], "v": cle[1],
                "cost": round(cost, 1),
                "statut": statut,
            })

    ajouter_fibre("TEL_01", "TEL_02", 45.0)
    ajouter_fibre("TEL_02", "TEL_04", 55.0)
    ajouter_fibre("TEL_04", "TEL_03", 40.0)
    ajouter_fibre("TEL_03", "TEL_01", 35.0)

    for u_id in all_ids:
        ux, uy = sites[u_id]["_x"], sites[u_id]["_y"]
        voisins = sorted(
            [v for v in all_ids if v != u_id],
            key=lambda v: math.hypot(ux - sites[v]["_x"], uy - sites[v]["_y"])
        )
        for v_id in voisins[:2]:
            dist = math.hypot(ux - sites[v_id]["_x"], uy - sites[v_id]["_y"])
            cost = max(3.0, dist * 2.5 + rng.uniform(0.5, 3.0))
            ajouter_fibre(u_id, v_id, cost)

    # 25 demandes d'interventions
    types_urg = ["incendie", "accident", "urgence_medicale", "malaise", "fuite_gaz"]
    priorites = ["critique", "haute", "normale", "basse"]
    quartiers_ids = [s for s in all_ids if s.startswith("QUA_")]
    demande_sites = rng.sample(quartiers_ids, 25)
    demandes = []
    for idx, s in enumerate(demande_sites, start=1):
        demandes.append({
            "id": f"DEM_{str(idx).zfill(3)}",
            "origine": s,
            "type": rng.choice(types_urg),
            "priorite": rng.choices(priorites, weights=[0.2, 0.4, 0.3, 0.1], k=1)[0],
        })

    # scenarios d'incidents
    scenarios = [
        {"scenario": "fermeture_pont_central", "action": "fermer_route", "u": "CAS_01", "v": "HOP_01", "valeur": ""},
        {"scenario": "fermeture_pont_central", "action": "fermer_route", "u": "HOP_01", "v": "CAS_01", "valeur": ""},
        {"scenario": "heure_pointe_generale", "action": "heure_pointe", "u": "", "v": "", "valeur": ""},
        {"scenario": "panne_fibre_backbone_sud", "action": "fermer_fibre", "u": "TEL_01", "v": "TEL_02", "valeur": ""},
        {"scenario": "travaux_boulevard_est", "action": "modifier_temps", "u": "CAS_04", "v": "TEL_04", "valeur": "35.0"},
    ]

    for s in sites.values():
        s.pop("_x", None)
        s.pop("_y", None)

    sauvegarder_sites(dossier / "sites.csv", sites)
    sauvegarder_routes(dossier / "routes.csv", routes)
    sauvegarder_fibre(dossier / "fibre.csv", fibre)
    sauvegarder_demandes(dossier / "demandes.csv", demandes)
    sauvegarder_scenarios(dossier / "scenarios.csv", scenarios)


if __name__ == "__main__":
    construire_jeu_realiste()
