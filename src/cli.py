import argparse
import sys
from pathlib import Path

from src.io_donnees import valider_donnees, charger_jeu_donnees
from src.indicateurs import appliquer_scenario, orchestrer_module_5
from src.generateur import generer_jeu_donnees


def afficher_titre(titre):
    print("\n" + "=" * 60)
    print(f"  {titre}")
    print("=" * 60)


def cmd_valider(chemin_donnees):
    afficher_titre(f"Validation : {chemin_donnees}")
    est_valide, erreurs = valider_donnees(chemin_donnees, autoriser_temps_negatifs=False)

    if est_valide:
        print("[OK] Tous les fichiers CSV sont valides.")
        return 0
    else:
        print(f"[ERREUR] {len(erreurs)} erreur(s) trouvee(s) :")
        for err in erreurs:
            print(f"  - {err}")
        return 1


def cmd_resilience(chemin_donnees, nom_scenario=None):
    afficher_titre(f"Module 5 - Resilience : {chemin_donnees}")
    try:
        donnees = charger_jeu_donnees(chemin_donnees, valider=True)
    except Exception as e:
        print(f"[ERREUR] Chargement impossible : {e}")
        return 1

    resultat = orchestrer_module_5(donnees)
    tableau = resultat["tableau"]

    print("\n--- Tableau comparatif des scenarios ---")
    headers = ["Scenario", "Inacc.", "Tps moy", "Retard moy", "Retard max", "Comp. Fibre", "Cout repar."]
    print(f"{headers[0]:<35} | {headers[1]:<7} | {headers[2]:<9} | {headers[3]:<10} | {headers[4]:<10} | {headers[5]:<11} | {headers[6]:<11}")
    print("-" * 105)
    for row in tableau:
        sc = row["Scénario"][:34]
        inacc = str(row["Demandes inaccessibles"])
        tmoy = f"{row['Temps moyen (min)']:.1f}"
        rmoy = f"{row['Retard moyen (min)']:.1f}"
        rmax = f"{row['Retard max (min)']:.1f}"
        comp = str(row["Composantes Fibre"])
        cout = f"{row['Coût réparation fibre']:.1f}"
        print(f"{sc:<35} | {inacc:<7} | {tmoy:<9} | {rmoy:<10} | {rmax:<10} | {comp:<11} | {cout:<11}")

    print(f"\n[OK] Resultats ecrits dans {resultat['fichier_md']}")
    return 0


def cmd_itineraires(chemin_donnees, nom_scenario=None):
    afficher_titre(f"Module 2 - Itineraires : {chemin_donnees}")
    try:
        donnees = charger_jeu_donnees(chemin_donnees, valider=True)
    except Exception as e:
        print(f"[ERREUR] {e}")
        return 1

    g_routes = donnees["graphe_routes"]
    if nom_scenario:
        print(f"[INFO] Scenario applique : '{nom_scenario}'")
        g_routes = appliquer_scenario(g_routes, donnees["scenarios"], nom_scenario=nom_scenario)

    try:
        from src import chemins
        print("[INFO] Calcul via chemins.py de B...")
        casernes = [s for s, a in donnees["sites"].items() if a.get("type") == "caserne"]
        for c in casernes:
            dist, _ = chemins.dijkstra(g_routes, c)
            nb = len([d for d in dist.values() if d < float('inf')])
            print(f"  Caserne {c} : {nb} sites atteignables.")
    except (ImportError, AttributeError):
        print("[INFO] Module chemins.py (B) pas encore livre. Calcul de secours interne...")
        from src.indicateurs import evaluer_resilience_demandes
        casernes = [s for s, a in donnees["sites"].items() if a.get("type") == "caserne"]
        res = evaluer_resilience_demandes(g_routes, casernes, donnees["demandes"])
        print(f"  Demandes traitees : {res['total_demandes']}")
        print(f"  Demandes inaccessibles : {res['inaccessibles']}")
        print(f"  Temps moyen intervention : {res['temps_moyen']} min")

    return 0


def cmd_accessibilite(chemin_donnees):
    afficher_titre(f"Module 1 - Accessibilite : {chemin_donnees}")
    donnees = charger_jeu_donnees(chemin_donnees, valider=True)
    try:
        from src import parcours
        print("[INFO] Appel parcours.py (B)...")
    except (ImportError, AttributeError):
        print("[INFO] Module parcours.py (B) en attente.")
        g = donnees["graphe_routes"]
        print(f"  Graphe routier : {g.nombre_sommets()} sommets, {g.nombre_arcs()} arcs.")
    return 0


def cmd_mst(chemin_donnees):
    afficher_titre(f"Module 4 - Fibre ACM : {chemin_donnees}")
    donnees = charger_jeu_donnees(chemin_donnees, valider=True)
    g_fibre = donnees["graphe_fibre"]
    try:
        from src import arbres
        print("[INFO] Appel arbres.py (C)...")
    except (ImportError, AttributeError):
        print("[INFO] Module arbres.py (C) en attente.")
        print(f"  Graphe fibre : {g_fibre.nombre_sommets()} sommets, {g_fibre.nombre_arcs()} aretes.")
    return 0


def cmd_panne(chemin_donnees, nom_scenario=None):
    afficher_titre(f"Module 4 - Panne fibre : {chemin_donnees}")
    donnees = charger_jeu_donnees(chemin_donnees, valider=True)
    g_fibre = donnees["graphe_fibre"]
    sc = nom_scenario or "panne_fibre_troncon_central"
    g_perturbe = appliquer_scenario(g_fibre, donnees["scenarios"], nom_scenario=sc)
    print(f"  Aretes avant panne : {g_fibre.nombre_arcs()}")
    print(f"  Aretes apres panne : {g_perturbe.nombre_arcs()}")
    return 0


def cmd_absorbant(chemin_donnees):
    afficher_titre("Module 3 - Circuits absorbants")
    try:
        from src import chemins
        print("[INFO] Verification circuits absorbants (B/C)...")
    except (ImportError, AttributeError):
        print("[INFO] Modules B et C requis pour le module 3.")
    return 0


def cmd_bench():
    afficher_titre("Benchmarks (C)")
    try:
        from src import benchmarks
        print("[INFO] Lancement benchmarks (C)...")
    except (ImportError, AttributeError):
        print("[INFO] Module benchmarks.py (C) en attente.")
    return 0


def main(arguments=None):
    parser = argparse.ArgumentParser(
        prog="novapolis",
        description="Novapolis Resilience - Outil d'analyse de reseau urbain",
    )

    parser.add_argument("--donnees", type=Path, default=Path("data/petit"), help="Dossier des CSV")
    parser.add_argument("--scenario", type=str, default=None, help="Nom du scenario a appliquer")
    parser.add_argument(
        "--operation",
        type=str,
        choices=["valider", "accessibilite", "itineraires", "mst", "panne", "absorbant", "resilience", "bench"],
        default="resilience",
        help="Action a executer",
    )
    parser.add_argument("--generer", action="store_true", help="Generer un graphe aleatoire")
    parser.add_argument("--sommets", type=int, default=100, help="Nombre de sommets")
    parser.add_argument("--densite", type=float, default=3.0, help="Densite m / n")
    parser.add_argument("--graine", type=int, default=42, help="Graine aleatoire")
    parser.add_argument("--sortie", type=Path, default=Path("data/genere"), help="Dossier de sortie")

    args = parser.parse_args(arguments)

    if args.generer:
        afficher_titre(f"Generation ({args.sommets} sommets, graine={args.graine})")
        info = generer_jeu_donnees(
            n_sommets=args.sommets,
            densite=args.densite,
            graine=args.graine,
            dossier_sortie=args.sortie,
        )
        print(f"[OK] Donnees generees dans {args.sortie} ({info['n_sommets']} sommets, {info['n_arcs_routes']} arcs).")
        return 0

    if args.operation == "valider":
        return cmd_valider(args.donnees)
    elif args.operation == "resilience":
        return cmd_resilience(args.donnees, args.scenario)
    elif args.operation == "itineraires":
        return cmd_itineraires(args.donnees, args.scenario)
    elif args.operation == "accessibilite":
        return cmd_accessibilite(args.donnees)
    elif args.operation == "mst":
        return cmd_mst(args.donnees)
    elif args.operation == "panne":
        return cmd_panne(args.donnees, args.scenario)
    elif args.operation == "absorbant":
        return cmd_absorbant(args.donnees)
    elif args.operation == "bench":
        return cmd_bench()

    return 0


if __name__ == "__main__":
    sys.exit(main())
