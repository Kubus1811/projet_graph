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

    try:
        resultat = orchestrer_module_5(donnees)
    except ValueError as e:
        print(f"[ERREUR] {e}")
        return 1
    tableau = resultat["tableau"]

    print("\n--- Tableau comparatif des scenarios ---")
    headers = ["Scenario", "Inacc.", "Tps moy", "Retard moy", "Retard max", "Sensibles", "Comp. Fibre", "Cout repar."]
    print(f"{headers[0]:<35} | {headers[1]:<7} | {headers[2]:<9} | {headers[3]:<10} | {headers[4]:<10} | {headers[5]:<9} | {headers[6]:<11} | {headers[7]:<11}")
    print("-" * 117)
    for row in tableau:
        sc = row["Scénario"][:34]
        inacc = str(row["Demandes inaccessibles"])
        tmoy = f"{row['Temps moyen (min)']:.1f}"
        rmoy = f"{row['Retard moyen (min)']:.1f}"
        rmax = f"{row['Retard max (min)']:.1f}"
        sens = f"{row['Sites sensibles accessibles (%)']:.0f} %"
        comp = str(row["Composantes Fibre"])
        cout = f"{row['Coût réparation fibre']:.1f}"
        print(f"{sc:<35} | {inacc:<7} | {tmoy:<9} | {rmoy:<10} | {rmax:<10} | {sens:<9} | {comp:<11} | {cout:<11}")

    print(f"\n[OK] Resultats ecrits dans {resultat['fichier_md']}")
    return 0


def cmd_itineraires(chemin_donnees, nom_scenario=None):
    afficher_titre(f"Module 2 - Itineraires : {chemin_donnees}")
    try:
        donnees = charger_jeu_donnees(chemin_donnees, valider=True)
    except Exception as e:
        print(f"[ERREUR] {e}")
        return 1

    from src import chemins

    g_ref = donnees["graphe_routes"]
    casernes = [s for s, a in donnees["sites"].items() if a.get("type") == "caserne"]

    if not nom_scenario:
        its = chemins.itineraires_demandes(g_ref, donnees["demandes"], casernes)
        print(f"{'Demande':<10} {'Site':<10} {'Caserne':<10} {'Duree':>7} {'Arcs':>5}  Chemin")
        print("-" * 90)
        for it in its:
            if it["accessible"]:
                print(f"{it['demande']:<10} {it['cible']:<10} {it['caserne']:<10} {it['duree']:>7.1f} "
                      f"{it['nb_arcs']:>5}  {' -> '.join(it['chemin'])}")
                if it["fermetures"]:
                    print(f"{'':<46}travaux : {it['fermetures']}")
            else:
                print(f"{it['demande']:<10} {it['cible']:<10} {'-':<10} {'INACCESSIBLE':>13}")
        diff = chemins.comparer_algorithmes(g_ref, sources=casernes, avec_floyd=g_ref.nombre_sommets() <= 400)
        print(f"\n[INFO] Dijkstra / Bellman-Ford / Floyd-Warshall concordants : {'oui' if not diff else 'NON'}")
        return 0

    print(f"[INFO] Scenario applique : '{nom_scenario}' (sur une copie)")
    g_sc = appliquer_scenario(g_ref, donnees["scenarios"], nom_scenario=nom_scenario)
    lignes = chemins.comparer_scenario(g_ref, g_sc, donnees["demandes"], casernes)

    print(f"{'Demande':<10} {'Site':<10} {'Avant':>7} {'Apres':>7} {'Retard':>7} {'Rel.':>7}  Chemin apres")
    print("-" * 90)
    for l in lignes:
        apres = f"{l['cout_apres']:.1f}" if l["accessible_apres"] else "INACC."
        retard = f"{l['retard_absolu']:+.1f}" if l["retard_absolu"] is not None else "-"
        rel = f"{l['retard_relatif']:+.0%}" if l["retard_relatif"] is not None else "-"
        chemin = " -> ".join(l["chemin_apres"]) if l["chemin_apres"] else "-"
        print(f"{l['demande']:<10} {l['site']:<10} {l['cout_avant']:>7.1f} {apres:>7} {retard:>7} {rel:>7}  {chemin}")
        if l["fermetures_rencontrees"]:
            print(f"{'':<54}fermetures evitees : {l['fermetures_rencontrees']}")

    ind = chemins.indicateurs_routes(lignes, g_sc, casernes)
    print("\n--- Indicateurs routes ---")
    print(f"  Demandes devenues inaccessibles : {len(ind['demandes_devenues_inaccessibles'])} {ind['demandes_devenues_inaccessibles']}")
    print(f"  Demandes retardees              : {ind['nb_demandes_retardees']} / {ind['nb_demandes']}")
    print(f"  Retard moyen / max              : {ind['retard_moyen']:.2f} / {ind['retard_max']:.2f} min")
    print(f"  Sites sensibles accessibles     : {ind['proportion_sensibles_accessibles']:.0%}")
    return 0


def cmd_accessibilite(chemin_donnees, nom_scenario=None):
    afficher_titre(f"Module 1 - Accessibilite : {chemin_donnees}")
    donnees = charger_jeu_donnees(chemin_donnees, valider=True)
    from src import parcours

    g = donnees["graphe_routes"]
    if nom_scenario:
        print(f"[INFO] Scenario applique : '{nom_scenario}' (sur une copie)")
        g = appliquer_scenario(g, donnees["scenarios"], nom_scenario=nom_scenario)

    diag = parcours.diagnostic_accessibilite(g)
    print(f"  Graphe routier : {g.nombre_sommets()} sommets, {g.nombre_arcs()} arcs.")
    print(f"  Casernes : {', '.join(diag['casernes'])}")
    print("\n--- Accessibilite depuis les casernes (BFS multi-sources) ---")
    print(f"  Sites atteignables      : {diag['nb_atteignables']} / {diag['nb_sites']}")
    print(f"  Sites non atteignables  : {diag['non_atteignables'] or 'aucun'}")
    print(f"  Sites isoles (sans arc) : {diag['isoles'] or 'aucun'}")
    print(f"  Sites sensibles atteints: {diag['sensibles_accessibles']} / {diag['sensibles_total']}"
          + (f"  (manquants : {diag['sensibles_non_accessibles']})" if diag["sensibles_non_accessibles"] else ""))
    print("\n--- Connexite ---")
    print(f"  Composantes connexes (sens ignore) : {diag['nb_composantes_connexes']}")
    print(f"  Composantes fortement connexes     : {diag['nb_cfc']} (la plus grande : {diag['plus_grande_cfc']} sites)")
    petites = [c for c in diag["cfc"] if len(c) < diag["plus_grande_cfc"]]
    if petites:
        print(f"  Hors de la grande CFC : {petites[:10]}{' ...' if len(petites) > 10 else ''}")
    circuit = diag["circuit_exemple"]
    print(f"  Circuit oriente trouve : {' -> '.join(circuit) if circuit else 'aucun'}")
    return 0


def cmd_mst(chemin_donnees):
    afficher_titre(f"Module 4 - Fibre ACM : {chemin_donnees}")
    donnees = charger_jeu_donnees(chemin_donnees, valider=True)
    g_fibre = donnees["graphe_fibre"]
    from src import arbres
    print(arbres.formater_comparaison_acm(g_fibre))
    return 0


def cmd_panne(chemin_donnees, nom_scenario=None):
    afficher_titre(f"Module 4 - Panne fibre : {chemin_donnees}")
    donnees = charger_jeu_donnees(chemin_donnees, valider=True)
    g_fibre = donnees["graphe_fibre"]
    regles = [r for r in donnees["scenarios"] if r["action"] == "fermer_fibre"]
    # sans scenario precise on prend la premiere panne du fichier
    sc = nom_scenario or (regles[0]["scenario"] if regles else None)
    regles = [r for r in regles if r["scenario"] == sc]

    if not regles:
        print(f"[ERREUR] Aucune panne de fibre pour le scenario '{sc}'.")
        return 1

    from src import arbres
    print(f"[INFO] Scenario : '{sc}'")
    for r in regles:
        try:
            print(arbres.formater_panne(arbres.analyser_panne(g_fibre, r["u"], r["v"])))
        except ValueError as e:
            print(f"[ERREUR] {e}")
            return 1
    return 0


def cmd_absorbant(chemin_donnees, source=None):
    afficher_titre(f"Module 3 - Circuits absorbants : {chemin_donnees}")
    from src import absorbants

    try:
        # les couts negatifs sont autorises ici : c'est tout l'objet du module 3
        donnees = charger_jeu_donnees(chemin_donnees, valider=True, autoriser_temps_negatifs=True)
        g = donnees["graphe_routes"]
        if source:
            sources = [source]
        else:
            sources = [s for s, a in donnees["sites"].items() if a.get("type") == "caserne"] or g.sommets()[:1]
        print(absorbants.formater_circuits_absorbants(absorbants.analyser_circuits_absorbants(g, sources)))
    except (ValueError, KeyError) as e:
        print(f"[ERREUR] {e}")
        return 1
    return 0


def cmd_bench(graine):
    afficher_titre(f"Benchmarks (graine={graine})")
    from src import benchmarks
    resultat = benchmarks.lancer_benchmarks(graine=graine)
    print(benchmarks.formater_benchmarks(resultat["lignes"]))
    print(f"\n[OK] Resultats ecrits dans {resultat['fichier_csv']}")
    for fichier in benchmarks.tracer_graphiques(resultat["lignes"]):
        print(f"[OK] Graphique ecrit dans {fichier}")
    return 0


def cmd_localite(graine):
    afficher_titre(f"Experience de localite memoire (graine={graine})")
    from src import benchmarks
    resultat = benchmarks.experience_localite(graine=graine)
    print(benchmarks.formater_localite(resultat["lignes"]))
    print(f"\n[OK] Resultats ecrits dans {resultat['fichier_csv']}")
    print(f"[OK] Graphique ecrit dans {benchmarks.tracer_localite(resultat['lignes'])}")
    return 0


def cmd_site(port):
    from src import site_web
    site_web.lancer(port)
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
        choices=["valider", "accessibilite", "itineraires", "mst", "panne", "absorbant", "resilience", "bench", "localite", "site"],
        default="resilience",
        help="Action a executer",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port du site (operation site)")
    parser.add_argument("--source", type=str, default=None, help="Sommet de depart (operation absorbant)")
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
        return cmd_accessibilite(args.donnees, args.scenario)
    elif args.operation == "mst":
        return cmd_mst(args.donnees)
    elif args.operation == "panne":
        return cmd_panne(args.donnees, args.scenario)
    elif args.operation == "absorbant":
        return cmd_absorbant(args.donnees, args.source)
    elif args.operation == "bench":
        return cmd_bench(args.graine)
    elif args.operation == "localite":
        return cmd_localite(args.graine)
    elif args.operation == "site":
        return cmd_site(args.port)

    return 0


if __name__ == "__main__":
    sys.exit(main())
