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


def generer_jeu_donnees(n_sommets=100, densite=3.0, graine=42, dossier_sortie="data/genere",
                        prefixe_id="S", largeur_grille=100.0):
    if n_sommets < 4:
        raise ValueError("Il faut au moins 4 sommets.")

    # graine fixee pour que le resultat soit toujours identique
    rng = random.Random(graine)
    dossier = Path(dossier_sortie)
    dossier.mkdir(parents=True, exist_ok=True)

    pad = max(3, len(str(n_sommets)))

    types_possibles = ["caserne", "hopital", "telecom", "ecole", "quartier"]
    poids_types = [0.03, 0.03, 0.04, 0.10, 0.80]

    sites = {}
    points = []

    for i in range(1, n_sommets + 1):
        s_id = f"{prefixe_id}{str(i).zfill(pad)}"
        if i == 1:
            t = "caserne"
        elif i == 2:
            t = "hopital"
        elif i == 3:
            t = "telecom"
        elif i == 4:
            t = "caserne"
        else:
            t = rng.choices(types_possibles, weights=poids_types, k=1)[0]

        x = round(rng.uniform(0.0, largeur_grille), 4)
        y = round(rng.uniform(0.0, largeur_grille), 4)

        sites[s_id] = {
            "nom": f"{t.capitalize()} {s_id}",
            "type": t,
            "longitude": round(2.30 + (x / 100.0) * 0.15, 6),
            "latitude": round(48.80 + (y / 100.0) * 0.15, 6),
            "_x": x,
            "_y": y,
        }
        points.append((s_id, x, y))

    # decoupage en grille pour trouver les voisins rapidement sans O(n^2)
    taille_cellule = max(largeur_grille / max(1, int(math.sqrt(n_sommets) / 2)), 5.0)
    grille_cellules = {}
    for s_id, x, y in points:
        cx, cy = int(x // taille_cellule), int(y // taille_cellule)
        grille_cellules.setdefault((cx, cy), []).append((s_id, x, y))

    def sommets_proches(s_id, x, y, k=8):
        cx, cy = int(x // taille_cellule), int(y // taille_cellule)
        candidats = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for v_id, vx, vy in grille_cellules.get((cx + dx, cy + dy), []):
                    if v_id != s_id:
                        d = math.hypot(x - vx, y - vy)
                        candidats.append((v_id, d))
        if len(candidats) < k:
            for v_id, vx, vy in points:
                if v_id != s_id:
                    d = math.hypot(x - vx, y - vy)
                    candidats.append((v_id, d))
        candidats.sort(key=lambda item: item[1])
        return candidats[:k]

    # reseau routier oriente
    arcs_routier_set = set()
    arcs_routier = []

    # chaine principale pour eviter les sommets isoles
    for idx in range(n_sommets - 1):
        u = points[idx][0]
        v = points[idx + 1][0]
        d = math.hypot(points[idx][1] - points[idx + 1][1], points[idx][2] - points[idx + 1][2])
        t_norm = round(max(1.0, d * 1.5 + rng.uniform(0.5, 2.0)), 1)
        t_pte = round(t_norm * rng.uniform(1.3, 2.2), 1)
        arcs_routier_set.add((u, v))
        arcs_routier.append({"u": u, "v": v, "temps_normal": t_norm, "temps_pointe": t_pte, "statut": "ouvert"})
        if rng.random() < 0.8:
            arcs_routier_set.add((v, u))
            arcs_routier.append({"u": v, "v": u, "temps_normal": t_norm, "temps_pointe": t_pte, "statut": "ouvert"})

    cible_arcs = int(n_sommets * densite)
    for s_id, x, y in points:
        if len(arcs_routier) >= cible_arcs:
            break
        voisins = sommets_proches(s_id, x, y, k=6)
        for v_id, dist in voisins:
            if len(arcs_routier) >= cible_arcs:
                break
            if (s_id, v_id) not in arcs_routier_set:
                t_norm = round(max(1.0, dist * 1.4 + rng.uniform(0.2, 1.5)), 1)
                t_pte = round(t_norm * rng.uniform(1.2, 2.0), 1)
                statut = "travaux" if rng.random() < 0.03 else "ouvert"
                arcs_routier_set.add((s_id, v_id))
                arcs_routier.append({"u": s_id, "v": v_id, "temps_normal": t_norm, "temps_pointe": t_pte, "statut": statut})
                if rng.random() < 0.7 and (v_id, s_id) not in arcs_routier_set:
                    arcs_routier_set.add((v_id, s_id))
                    arcs_routier.append({"u": v_id, "v": s_id, "temps_normal": t_norm, "temps_pointe": t_pte, "statut": statut})

    # reseau fibre non oriente
    aretes_fibre_set = set()
    aretes_fibre = []
    for s_id, x, y in points:
        voisins = sommets_proches(s_id, x, y, k=4)
        for v_id, dist in voisins:
            cle = (s_id, v_id) if s_id <= v_id else (v_id, s_id)
            if cle not in aretes_fibre_set:
                cout = round(max(2.0, dist * 3.0 + rng.uniform(1.0, 5.0)), 1)
                aretes_fibre_set.add(cle)
                aretes_fibre.append({"u": cle[0], "v": cle[1], "cost": cout, "statut": "ouvert"})

    # demandes d'urgence
    types_urgences = ["incendie", "accident", "malaise", "materiel"]
    priorites = ["critique", "haute", "normale", "basse"]
    nb_demandes = min(50, max(5, n_sommets // 4))
    demandes = []

    sites_demandes = rng.sample(list(sites.keys()), nb_demandes)
    for idx, s_origine in enumerate(sites_demandes, start=1):
        demandes.append({
            "id": f"D{str(idx).zfill(3)}",
            "origine": s_origine,
            "type": rng.choice(types_urgences),
            "priorite": rng.choices(priorites, weights=[0.15, 0.45, 0.30, 0.10], k=1)[0],
        })

    # scenarios d'exemples
    scenarios = []
    if arcs_routier:
        scenarios.append({
            "scenario": "fermeture_axe_majeur",
            "action": "fermer_route",
            "u": arcs_routier[0]["u"],
            "v": arcs_routier[0]["v"],
            "valeur": "",
        })
    scenarios.append({
        "scenario": "heure_pointe_generale",
        "action": "heure_pointe",
        "u": "",
        "v": "",
        "valeur": "",
    })
    if aretes_fibre:
        scenarios.append({
            "scenario": "panne_fibre_troncon",
            "action": "fermer_fibre",
            "u": aretes_fibre[0]["u"],
            "v": aretes_fibre[0]["v"],
            "valeur": "",
        })

    for s in sites.values():
        s.pop("_x", None)
        s.pop("_y", None)

    sauvegarder_sites(dossier / "sites.csv", sites)
    sauvegarder_routes(dossier / "routes.csv", arcs_routier)
    sauvegarder_fibre(dossier / "fibre.csv", aretes_fibre)
    sauvegarder_demandes(dossier / "demandes.csv", demandes)
    sauvegarder_scenarios(dossier / "scenarios.csv", scenarios)

    return {
        "n_sommets": n_sommets,
        "n_arcs_routes": len(arcs_routier),
        "n_aretes_fibre": len(aretes_fibre),
        "n_demandes": len(demandes),
        "graine": graine,
        "dossier": str(dossier),
    }
