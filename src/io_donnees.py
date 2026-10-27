import csv
from pathlib import Path
from src.graphe import Graphe


class ErreurValidationDonnees(Exception):
    pass


def valider_fichier_sites(chemin):
    erreurs = []
    chemin = Path(chemin)
    if not chemin.exists():
        return [f"Fichier manquant : {chemin}"]

    colonnes_attendues = {"id", "nom", "type", "longitude", "latitude"}
    ids_vus = set()

    with open(chemin, mode="r", encoding="utf-8-sig") as f:
        lecteur = csv.DictReader(f)
        if lecteur.fieldnames is None:
            return [f"{chemin.name} : fichier vide ou sans en-tête."]

        champs_presents = set(c.strip() for c in lecteur.fieldnames)
        manquants = colonnes_attendues - champs_presents
        if manquants:
            erreurs.append(f"{chemin.name} : colonnes obligatoires manquantes : {sorted(manquants)}")
            return erreurs

        for num_ligne, ligne in enumerate(lecteur, start=2):
            s_id = (ligne.get("id") or "").strip()
            if not s_id:
                erreurs.append(f"{chemin.name} ligne {num_ligne} : identifiant 'id' manquant ou vide.")
                continue
            if s_id in ids_vus:
                erreurs.append(f"{chemin.name} ligne {num_ligne} : identifiant en double '{s_id}'.")
            ids_vus.add(s_id)

            for coord in ("longitude", "latitude"):
                val = (ligne.get(coord) or "").strip()
                if val:
                    try:
                        float(val)
                    except ValueError:
                        erreurs.append(f"{chemin.name} ligne {num_ligne} : valeur non numérique '{val}' pour '{coord}'.")

    return erreurs


def valider_fichier_routes(chemin, sites_valides=None, autoriser_temps_negatifs=False):
    erreurs = []
    chemin = Path(chemin)
    if not chemin.exists():
        return [f"Fichier manquant : {chemin}"]

    colonnes_attendues = {"u", "v", "temps_normal", "temps_pointe", "statut"}

    with open(chemin, mode="r", encoding="utf-8-sig") as f:
        lecteur = csv.DictReader(f)
        if lecteur.fieldnames is None:
            return [f"{chemin.name} : fichier vide ou sans en-tête."]

        champs_presents = set(c.strip() for c in lecteur.fieldnames)
        manquants = colonnes_attendues - champs_presents
        if manquants:
            erreurs.append(f"{chemin.name} : colonnes obligatoires manquantes : {sorted(manquants)}")
            return erreurs

        for num_ligne, ligne in enumerate(lecteur, start=2):
            u = (ligne.get("u") or "").strip()
            v = (ligne.get("v") or "").strip()

            if not u or not v:
                erreurs.append(f"{chemin.name} ligne {num_ligne} : extrémité d'arc 'u' ou 'v' vide.")
                continue

            # verif si le sommet existe bien dans sites.csv
            if sites_valides is not None:
                if u not in sites_valides:
                    erreurs.append(f"{chemin.name} ligne {num_ligne} : site '{u}' inconnu.")
                if v not in sites_valides:
                    erreurs.append(f"{chemin.name} ligne {num_ligne} : site '{v}' inconnu.")

            for champ in ("temps_normal", "temps_pointe"):
                val_str = (ligne.get(champ) or "").strip()
                try:
                    val = float(val_str)
                    if val < 0 and not autoriser_temps_negatifs:
                        erreurs.append(f"{chemin.name} ligne {num_ligne} : temps négatif {val} interdit pour '{champ}'.")
                except ValueError:
                    erreurs.append(f"{chemin.name} ligne {num_ligne} : valeur non numérique '{val_str}' pour '{champ}'.")

    return erreurs


def valider_fichier_fibre(chemin, sites_valides=None):
    erreurs = []
    chemin = Path(chemin)
    if not chemin.exists():
        return [f"Fichier manquant : {chemin}"]

    colonnes_attendues = {"u", "v", "cost", "statut"}

    with open(chemin, mode="r", encoding="utf-8-sig") as f:
        lecteur = csv.DictReader(f)
        if lecteur.fieldnames is None:
            return [f"{chemin.name} : fichier vide ou sans en-tête."]

        champs_presents = set(c.strip() for c in lecteur.fieldnames)
        manquants = colonnes_attendues - champs_presents
        if manquants:
            erreurs.append(f"{chemin.name} : colonnes obligatoires manquantes : {sorted(manquants)}")
            return erreurs

        for num_ligne, ligne in enumerate(lecteur, start=2):
            u = (ligne.get("u") or "").strip()
            v = (ligne.get("v") or "").strip()

            if not u or not v:
                erreurs.append(f"{chemin.name} ligne {num_ligne} : extrémité d'arête 'u' ou 'v' vide.")
                continue

            if sites_valides is not None:
                if u not in sites_valides:
                    erreurs.append(f"{chemin.name} ligne {num_ligne} : site '{u}' inconnu.")
                if v not in sites_valides:
                    erreurs.append(f"{chemin.name} ligne {num_ligne} : site '{v}' inconnu.")

            val_str = (ligne.get("cost") or "").strip()
            try:
                val = float(val_str)
                if val < 0:
                    erreurs.append(f"{chemin.name} ligne {num_ligne} : coût négatif {val} interdit pour la fibre.")
            except ValueError:
                erreurs.append(f"{chemin.name} ligne {num_ligne} : valeur non numérique '{val_str}' pour 'cost'.")

    return erreurs


def valider_fichier_demandes(chemin, sites_valides=None):
    erreurs = []
    chemin = Path(chemin)
    if not chemin.exists():
        return [f"Fichier manquant : {chemin}"]

    colonnes_attendues = {"id", "origine", "type", "priorite"}
    ids_vus = set()

    with open(chemin, mode="r", encoding="utf-8-sig") as f:
        lecteur = csv.DictReader(f)
        if lecteur.fieldnames is None:
            return [f"{chemin.name} : fichier vide ou sans en-tête."]

        champs_presents = set(c.strip() for c in lecteur.fieldnames)
        manquants = colonnes_attendues - champs_presents
        if manquants:
            erreurs.append(f"{chemin.name} : colonnes obligatoires manquantes : {sorted(manquants)}")
            return erreurs

        for num_ligne, ligne in enumerate(lecteur, start=2):
            d_id = (ligne.get("id") or "").strip()
            if not d_id:
                erreurs.append(f"{chemin.name} ligne {num_ligne} : identifiant 'id' manquant.")
                continue
            if d_id in ids_vus:
                erreurs.append(f"{chemin.name} ligne {num_ligne} : identifiant en double '{d_id}'.")
            ids_vus.add(d_id)

            origine = (ligne.get("origine") or "").strip()
            if sites_valides is not None and origine not in sites_valides:
                erreurs.append(f"{chemin.name} ligne {num_ligne} : site d'origine '{origine}' inconnu.")

    return erreurs


def valider_fichier_scenarios(chemin, sites_valides=None):
    erreurs = []
    chemin = Path(chemin)
    if not chemin.exists():
        return []

    colonnes_attendues = {"scenario", "action", "u", "v", "valeur"}
    actions_valides = {"fermer_route", "modifier_temps", "heure_pointe", "fermer_fibre"}

    with open(chemin, mode="r", encoding="utf-8-sig") as f:
        lecteur = csv.DictReader(f)
        if lecteur.fieldnames is None:
            return [f"{chemin.name} : fichier vide ou sans en-tête."]

        champs_presents = set(c.strip() for c in lecteur.fieldnames)
        manquants = colonnes_attendues - champs_presents
        if manquants:
            erreurs.append(f"{chemin.name} : colonnes obligatoires manquantes : {sorted(manquants)}")
            return erreurs

        for num_ligne, ligne in enumerate(lecteur, start=2):
            action = (ligne.get("action") or "").strip()
            if action not in actions_valides:
                erreurs.append(f"{chemin.name} ligne {num_ligne} : action inconnue '{action}'.")

            u = (ligne.get("u") or "").strip()
            v = (ligne.get("v") or "").strip()

            if action in {"fermer_route", "modifier_temps", "fermer_fibre"}:
                if sites_valides is not None:
                    if u and u not in sites_valides:
                        erreurs.append(f"{chemin.name} ligne {num_ligne} : site '{u}' inconnu pour l'action '{action}'.")
                    if v and v not in sites_valides:
                        erreurs.append(f"{chemin.name} ligne {num_ligne} : site '{v}' inconnu pour l'action '{action}'.")

            if action == "modifier_temps":
                val_str = (ligne.get("valeur") or "").strip()
                try:
                    val = float(val_str)
                    if val < 0:
                        erreurs.append(f"{chemin.name} ligne {num_ligne} : temps modifié négatif {val}.")
                except ValueError:
                    erreurs.append(f"{chemin.name} ligne {num_ligne} : valeur non numérique '{val_str}'.")

    return erreurs


def valider_donnees(dossier, autoriser_temps_negatifs=False, lever_exception=False):
    dossier = Path(dossier)
    erreurs = []

    f_sites = dossier / "sites.csv"
    err_sites = valider_fichier_sites(f_sites)
    erreurs.extend(err_sites)

    sites_valides = set()
    if f_sites.exists() and not err_sites:
        sites_valides = set(charger_sites(f_sites).keys())

    erreurs.extend(valider_fichier_routes(dossier / "routes.csv", sites_valides, autoriser_temps_negatifs))
    erreurs.extend(valider_fichier_fibre(dossier / "fibre.csv", sites_valides))

    if (dossier / "demandes.csv").exists():
        erreurs.extend(valider_fichier_demandes(dossier / "demandes.csv", sites_valides))

    if (dossier / "scenarios.csv").exists():
        erreurs.extend(valider_fichier_scenarios(dossier / "scenarios.csv", sites_valides))

    est_valide = len(erreurs) == 0
    if not est_valide and lever_exception:
        msg = f"Validation echouee ({len(erreurs)} erreur(s)) :\n" + "\n".join(f" - {e}" for e in erreurs)
        raise ErreurValidationDonnees(msg)

    return est_valide, erreurs


def charger_sites(chemin):
    sites = {}
    with open(chemin, mode="r", encoding="utf-8-sig") as f:
        lecteur = csv.DictReader(f)
        for ligne in lecteur:
            s_id = ligne["id"].strip()
            sites[s_id] = {
                "nom": (ligne.get("nom") or "").strip(),
                "type": (ligne.get("type") or "").strip(),
                "longitude": float(ligne["longitude"]) if ligne.get("longitude") else 0.0,
                "latitude": float(ligne["latitude"]) if ligne.get("latitude") else 0.0,
            }
    return sites


def charger_routes(chemin, sites=None):
    g = Graphe(oriente=True)
    if sites:
        for s_id, attrs in sites.items():
            g.ajouter_sommet(s_id, **attrs)

    with open(chemin, mode="r", encoding="utf-8-sig") as f:
        lecteur = csv.DictReader(f)
        for ligne in lecteur:
            u = ligne["u"].strip()
            v = ligne["v"].strip()
            temps_normal = float(ligne["temps_normal"])
            temps_pointe = float(ligne.get("temps_pointe", temps_normal))
            statut = (ligne.get("statut") or "ouvert").strip()

            g.ajouter_arc(
                u, v,
                poids=temps_normal,
                temps_normal=temps_normal,
                temps_pointe=temps_pointe,
                statut=statut,
            )
    return g


def charger_fibre(chemin, sites=None):
    g = Graphe(oriente=False)
    if sites:
        for s_id, attrs in sites.items():
            g.ajouter_sommet(s_id, **attrs)

    with open(chemin, mode="r", encoding="utf-8-sig") as f:
        lecteur = csv.DictReader(f)
        for ligne in lecteur:
            u = ligne["u"].strip()
            v = ligne["v"].strip()
            cost = float(ligne["cost"])
            statut = (ligne.get("statut") or "ouvert").strip()

            g.ajouter_arc(
                u, v,
                poids=cost,
                cost=cost,
                statut=statut,
            )
    return g


def charger_demandes(chemin):
    chemin = Path(chemin)
    if not chemin.exists():
        return []
    demandes = []
    with open(chemin, mode="r", encoding="utf-8-sig") as f:
        lecteur = csv.DictReader(f)
        for ligne in lecteur:
            demandes.append({
                "id": ligne["id"].strip(),
                "origine": ligne["origine"].strip(),
                "type": (ligne.get("type") or "").strip(),
                "priorite": (ligne.get("priorite") or "").strip(),
            })
    return demandes


def charger_scenarios(chemin):
    chemin = Path(chemin)
    if not chemin.exists():
        return []
    scenarios = []
    with open(chemin, mode="r", encoding="utf-8-sig") as f:
        lecteur = csv.DictReader(f)
        for ligne in lecteur:
            scenarios.append({
                "scenario": ligne["scenario"].strip(),
                "action": ligne["action"].strip(),
                "u": (ligne.get("u") or "").strip(),
                "v": (ligne.get("v") or "").strip(),
                "valeur": (ligne.get("valeur") or "").strip(),
            })
    return scenarios


def charger_jeu_donnees(dossier, valider=True, autoriser_temps_negatifs=False):
    # charge tout le dossier en un seul appel
    dossier = Path(dossier)
    if valider:
        valider_donnees(dossier, autoriser_temps_negatifs=autoriser_temps_negatifs, lever_exception=True)

    sites = charger_sites(dossier / "sites.csv")
    g_routes = charger_routes(dossier / "routes.csv", sites=sites)
    g_fibre = charger_fibre(dossier / "fibre.csv", sites=sites)
    demandes = charger_demandes(dossier / "demandes.csv")
    scenarios = charger_scenarios(dossier / "scenarios.csv")

    return {
        "sites": sites,
        "graphe_routes": g_routes,
        "graphe_fibre": g_fibre,
        "demandes": demandes,
        "scenarios": scenarios,
    }


def sauvegarder_sites(chemin, sites):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, mode="w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "nom", "type", "longitude", "latitude"])
        w.writeheader()
        for s_id, attrs in sites.items():
            w.writerow({
                "id": s_id,
                "nom": attrs.get("nom", ""),
                "type": attrs.get("type", ""),
                "longitude": attrs.get("longitude", 0.0),
                "latitude": attrs.get("latitude", 0.0),
            })


def sauvegarder_routes(chemin, arcs):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, mode="w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["u", "v", "temps_normal", "temps_pointe", "statut"])
        w.writeheader()
        for arc in arcs:
            w.writerow({
                "u": arc["u"],
                "v": arc["v"],
                "temps_normal": arc["temps_normal"],
                "temps_pointe": arc.get("temps_pointe", arc["temps_normal"]),
                "statut": arc.get("statut", "ouvert"),
            })


def sauvegarder_fibre(chemin, aretes):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, mode="w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["u", "v", "cost", "statut"])
        w.writeheader()
        for a in aretes:
            w.writerow({
                "u": a["u"],
                "v": a["v"],
                "cost": a["cost"],
                "statut": a.get("statut", "ouvert"),
            })


def sauvegarder_demandes(chemin, demandes):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, mode="w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "origine", "type", "priorite"])
        w.writeheader()
        for d in demandes:
            w.writerow({
                "id": d["id"],
                "origine": d["origine"],
                "type": d.get("type", "urgence"),
                "priorite": d.get("priorite", "haute"),
            })


def sauvegarder_scenarios(chemin, scenarios):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, mode="w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scenario", "action", "u", "v", "valeur"])
        w.writeheader()
        for s in scenarios:
            w.writerow({
                "scenario": s["scenario"],
                "action": s["action"],
                "u": s.get("u", ""),
                "v": s.get("v", ""),
                "valeur": s.get("valeur", ""),
            })
