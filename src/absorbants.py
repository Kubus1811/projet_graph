from src.chemins import INF, MOINS_INF, bellman_ford_detail, sommets_diagonale_negative

SUPER_SOURCE = "__super_source__"
# au-dela, floyd-warshall en O(n^3) devient trop lent en python
TAILLE_MAX_FLOYD = 400


def circuit_existe(graphe):
    # super-source reliee a tous les sommets avec un cout 0 : tout devient atteignable,
    # donc bellman-ford voit aussi les circuits que la vraie source n'atteint pas
    g = graphe.copie()
    for s in graphe.sommets():
        g.ajouter_arc(SUPER_SOURCE, s, 0.0)
    return bellman_ford_detail(g, SUPER_SOURCE)["circuit_absorbant"]


def sommets_sur_un_circuit(graphe):
    # diagonale de floyd-warshall : L[i][i] < 0 si i est sur un circuit absorbant
    if graphe.nombre_sommets() > TAILLE_MAX_FLOYD:
        return None
    return sommets_diagonale_negative(graphe)


def analyser_circuits_absorbants(graphe, sources):
    par_source = {}
    for s in sources:
        res = bellman_ford_detail(graphe, s)
        dist = res["dist"]
        par_source[str(s)] = {
            "circuit_accessible": res["circuit_absorbant"],
            "diminuables": sorted(v for v, d in dist.items() if d == MOINS_INF),
            "inaccessibles": sorted(v for v, d in dist.items() if d == INF),
            "distances": dist,
        }

    return {
        "circuit_existe": circuit_existe(graphe),
        "sommets_sur_circuit": sommets_sur_un_circuit(graphe),
        "sources": par_source,
    }


def _distance(d):
    if d == MOINS_INF:
        return "-inf (diminuable sans fin)"
    if d == INF:
        return "inf (inaccessible)"
    return f"{d:.2f}"


def formater_circuits_absorbants(analyse):
    lignes = [f"Circuit absorbant dans le graphe : {'oui' if analyse['circuit_existe'] else 'non'}"]
    sur_circuit = analyse["sommets_sur_circuit"]
    if sur_circuit is None:
        lignes.append(f"  (liste des sommets non calculee : plus de {TAILLE_MAX_FLOYD} sommets pour Floyd-Warshall)")
    elif sur_circuit:
        lignes.append(f"  Sommets sur un circuit (diagonale de Floyd-Warshall) : {sur_circuit}")

    for s, r in analyse["sources"].items():
        lignes.append("")
        accessible = "oui" if r["circuit_accessible"] else "non"
        lignes.append(f"Depuis {s} : circuit accessible = {accessible}")
        if r["diminuables"]:
            lignes.append(f"  Distances -inf : {r['diminuables']}")
        if r["inaccessibles"]:
            lignes.append(f"  Inaccessibles  : {r['inaccessibles']}")
        # les distances ne s'affichent en entier que sur les petits graphes
        if len(r["distances"]) <= 20:
            for v, d in sorted(r["distances"].items()):
                lignes.append(f"    {v} : {_distance(d)}")

    if analyse["circuit_existe"]:
        lignes.append("")
        lignes.append("Rappel : ces couts negatifs sont un jeu de test artificiel, pas des durees reelles.")
    return "\n".join(lignes)
