import heapq
from collections import deque

from src.graphe import reconstruire_chemin
from src.parcours import arc_ouvert, successeurs_ouverts, casernes_du_graphe, _verifier_source


INF = float("inf")
MOINS_INF = float("-inf")


class PoidsNegatifErreur(ValueError):
    pass


def _arcs_ouverts(graphe):
    arcs = []
    for u in graphe.sommets():
        for v, poids in successeurs_ouverts(graphe, u):
            arcs.append((u, v, poids))
    return arcs


# ---------------------------------------------------------------- B7 : Dijkstra


def dijkstra(graphe, source):
    # tas binaire + suppression paresseuse, renvoie (dist, pred)
    return dijkstra_multi_sources(graphe, [source])[:2]


def dijkstra_multi_sources(graphe, sources):
    # toutes les sources a distance 0 dans le tas au depart
    # renvoie (dist, pred, origine) avec origine[v] = source la plus proche
    sources = [_verifier_source(graphe, s) for s in sources]

    for u, v, poids in _arcs_ouverts(graphe):
        if poids < 0:
            raise PoidsNegatifErreur(
                f"Dijkstra refuse les poids negatifs : arc {u} -> {v} de poids {poids}. "
                "Utiliser Bellman-Ford."
            )

    dist = {s: INF for s in graphe.sommets()}
    pred = {s: None for s in graphe.sommets()}
    origine = {s: None for s in graphe.sommets()}
    tas = []
    for s in sources:
        dist[s] = 0.0
        origine[s] = s
        heapq.heappush(tas, (0.0, s))

    while tas:
        d_u, u = heapq.heappop(tas)
        if d_u > dist[u]:
            # entree perimee, on l'ignore
            continue
        for v, poids in successeurs_ouverts(graphe, u):
            nd = d_u + poids
            if nd < dist[v]:
                dist[v] = nd
                pred[v] = u
                origine[v] = origine[u]
                heapq.heappush(tas, (nd, v))

    return dist, pred, origine


# ---------------------------------------------------------------- B8 : Bellman-Ford


def bellman_ford_detail(graphe, source):
    # |V|-1 passes avec arret anticipe, puis une passe de detection
    # renvoie un dict : dist, pred, circuit_absorbant, relachables, nb_passes
    source = _verifier_source(graphe, source)
    sommets = graphe.sommets()
    arcs = _arcs_ouverts(graphe)

    dist = {s: INF for s in sommets}
    pred = {s: None for s in sommets}
    dist[source] = 0.0

    nb_passes = 0
    for _ in range(len(sommets) - 1):
        nb_passes += 1
        modifie = False
        for u, v, poids in arcs:
            if dist[u] != INF and dist[u] + poids < dist[v]:
                dist[v] = dist[u] + poids
                pred[v] = u
                modifie = True
        if not modifie:
            break

    # passe |V| : un sommet encore relachable est influence par un circuit absorbant
    relachables = []
    for u, v, poids in arcs:
        if dist[u] != INF and dist[u] + poids < dist[v]:
            relachables.append(v)

    # tout ce qui est atteignable depuis un sommet relachable vaut -inf
    if relachables:
        file = deque(relachables)
        vus = set(relachables)
        while file:
            u = file.popleft()
            dist[u] = MOINS_INF
            for v, _ in successeurs_ouverts(graphe, u):
                if v not in vus:
                    vus.add(v)
                    file.append(v)

    return {
        "dist": dist,
        "pred": pred,
        "circuit_absorbant": bool(relachables),
        "relachables": sorted(set(relachables)),
        "nb_passes": nb_passes,
    }


def bellman_ford(graphe, source):
    res = bellman_ford_detail(graphe, source)
    return res["dist"], res["pred"]


# ---------------------------------------------------------------- B9 : Floyd-Warshall


def _floyd_warshall_brut(graphe):
    # L[i][j] distance, P[i][j] = predecesseur de j sur le chemin depuis i (indices)
    ids = graphe.sommets()
    n = len(ids)
    index = {s: k for k, s in enumerate(ids)}

    L = [[INF] * n for _ in range(n)]
    P = [[None] * n for _ in range(n)]
    for i in range(n):
        L[i][i] = 0.0
    for u, v, poids in _arcs_ouverts(graphe):
        i, j = index[u], index[v]
        if i == j:
            # boucle : utile seulement si negative
            if poids < L[i][i]:
                L[i][i] = poids
                P[i][i] = i
        elif poids < L[i][j]:
            L[i][j] = poids
            P[i][j] = i

    for k in range(n):
        Lk = L[k]
        Pk = P[k]
        for i in range(n):
            Lik = L[i][k]
            if Lik == INF:
                continue
            Li = L[i]
            Pi = P[i]
            for j in range(n):
                nd = Lik + Lk[j]
                if nd < Li[j]:
                    Li[j] = nd
                    Pi[j] = Pk[j]

    return ids, L, P


def floyd_warshall_matrices(graphe):
    ids, L, P = _floyd_warshall_brut(graphe)
    n = len(ids)

    # circuits absorbants : L[k][k] < 0, et tout i -> k -> j devient -inf
    absorbants = [k for k in range(n) if L[k][k] < 0]
    for k in absorbants:
        depuis_k = [j for j in range(n) if L[k][j] != INF]
        vers_k = [i for i in range(n) if L[i][k] != INF]
        for i in vers_k:
            for j in depuis_k:
                L[i][j] = MOINS_INF

    return ids, L, P


def floyd_warshall(graphe):
    # meme format que les autres : dist[s][t], pred[s] utilisable par reconstruire_chemin
    ids, L, P = floyd_warshall_matrices(graphe)
    dist = {}
    pred = {}
    for i, s in enumerate(ids):
        dist[s] = {t: L[i][j] for j, t in enumerate(ids)}
        pred[s] = {t: (ids[P[i][j]] if P[i][j] is not None and i != j else None) for j, t in enumerate(ids)}
    return dist, pred


def sommets_diagonale_negative(graphe):
    # lue avant le marquage -inf, qui toucherait tout sommet pouvant rejoindre un circuit et en revenir
    # une diagonale negative dit seulement qu'une boucle de cout negatif passe par ce sommet
    ids, L, _ = _floyd_warshall_brut(graphe)
    return sorted(ids[k] for k in range(len(ids)) if L[k][k] < 0)


def detecter_circuit_absorbant(graphe):
    # vrai si un circuit negatif existe n'importe ou (diagonale de FW)
    _, L, _ = floyd_warshall_matrices(graphe)
    return any(L[k][k] < 0 for k in range(len(L)))


# ---------------------------------------------------------------- B10 : reconstruction


def decrire_itineraire(graphe, dist, pred, source, cible):
    # chemin, duree, nb d'arcs et arcs non "ouvert" (travaux) rencontres
    source, cible = str(source), str(cible)
    d = dist.get(cible, INF)
    if d == MOINS_INF:
        return {"source": source, "cible": cible, "accessible": True, "chemin": None,
                "duree": MOINS_INF, "nb_arcs": None, "fermetures": []}
    chemin = reconstruire_chemin(pred, source, cible) if d != INF else None
    if chemin is None:
        return {"source": source, "cible": cible, "accessible": False, "chemin": None,
                "duree": INF, "nb_arcs": None, "fermetures": []}

    fermetures = []
    for u, v in zip(chemin, chemin[1:]):
        attrs = graphe.attributs_arc(u, v) or {}
        statut = str(attrs.get("statut", "ouvert")).strip().lower()
        if statut != "ouvert":
            fermetures.append((u, v, statut))

    return {"source": source, "cible": cible, "accessible": True, "chemin": chemin,
            "duree": d, "nb_arcs": len(chemin) - 1, "fermetures": fermetures}


# ---------------------------------------------------------------- B11 : itineraire par demande


def itineraires_demandes(graphe, demandes, casernes=None):
    # caserne retenue = la plus proche, en un seul dijkstra multi-sources
    if casernes is None:
        casernes = casernes_du_graphe(graphe)
    if not casernes:
        raise ValueError("Aucune caserne dans le graphe : impossible de calculer les itineraires.")
    dist, pred, origine = dijkstra_multi_sources(graphe, casernes)

    resultats = []
    for dem in demandes:
        cible = dem["origine"]
        if not graphe.a_sommet(cible):
            raise KeyError(f"Demande {dem['id']} : site '{cible}' absent du graphe.")
        caserne = origine.get(cible)
        if caserne is None:
            it = {"source": None, "cible": cible, "accessible": False, "chemin": None,
                  "duree": INF, "nb_arcs": None, "fermetures": []}
        else:
            it = decrire_itineraire(graphe, dist, pred, caserne, cible)
        it["demande"] = dem["id"]
        it["caserne"] = caserne
        it["type"] = dem.get("type", "")
        it["priorite"] = dem.get("priorite", "")
        resultats.append(it)
    return resultats


# ---------------------------------------------------------------- B12 : scenario de fermeture


def comparer_scenario(graphe_ref, graphe_scenario, demandes, casernes=None):
    # avant / apres pour chaque demande, le graphe de reference n'est pas modifie
    if casernes is None:
        casernes = casernes_du_graphe(graphe_ref)
    avant = {it["demande"]: it for it in itineraires_demandes(graphe_ref, demandes, casernes)}
    apres = {it["demande"]: it for it in itineraires_demandes(graphe_scenario, demandes, casernes)}

    lignes = []
    for dem in demandes:
        a = avant[dem["id"]]
        b = apres[dem["id"]]

        # arcs du chemin de reference qui n'existent plus ou sont fermes dans le scenario
        fermetures = []
        if a["chemin"]:
            for u, v in zip(a["chemin"], a["chemin"][1:]):
                attrs = graphe_scenario.attributs_arc(u, v)
                if attrs is None or not arc_ouvert(attrs):
                    fermetures.append((u, v))

        if a["accessible"] and b["accessible"]:
            retard_abs = b["duree"] - a["duree"]
            retard_rel = (retard_abs / a["duree"]) if a["duree"] > 0 else 0.0
        else:
            retard_abs = None
            retard_rel = None

        lignes.append({
            "demande": dem["id"],
            "site": dem["origine"],
            "priorite": dem.get("priorite", ""),
            "caserne_avant": a["caserne"],
            "caserne_apres": b["caserne"],
            "cout_avant": a["duree"],
            "cout_apres": b["duree"],
            "retard_absolu": retard_abs,
            "retard_relatif": retard_rel,
            "accessible_avant": a["accessible"],
            "accessible_apres": b["accessible"],
            "chemin_avant": a["chemin"],
            "chemin_apres": b["chemin"],
            "fermetures_rencontrees": fermetures,
        })
    return lignes


def indicateurs_routes(lignes_comparaison, graphe_scenario=None, casernes=None):
    # indicateurs du module 5 cote routes a partir de comparer_scenario
    from src.parcours import diagnostic_accessibilite

    devenues_inacc = [l["demande"] for l in lignes_comparaison
                      if l["accessible_avant"] and not l["accessible_apres"]]
    retards = [l["retard_absolu"] for l in lignes_comparaison if l["retard_absolu"] is not None]
    res = {
        "nb_demandes": len(lignes_comparaison),
        "demandes_devenues_inaccessibles": devenues_inacc,
        "nb_inaccessibles_apres": sum(1 for l in lignes_comparaison if not l["accessible_apres"]),
        "retard_moyen": (sum(retards) / len(retards)) if retards else 0.0,
        "retard_max": max(retards) if retards else 0.0,
        "nb_demandes_retardees": sum(1 for r in retards if r > 1e-9),
    }
    if graphe_scenario is not None:
        diag = diagnostic_accessibilite(graphe_scenario, casernes)
        total = diag["sensibles_total"]
        res["proportion_sensibles_accessibles"] = (diag["sensibles_accessibles"] / total) if total else 1.0
        res["sensibles_non_accessibles"] = diag["sensibles_non_accessibles"]
    return res


# ---------------------------------------------------------------- B13 : comparaison des 3 algos


def comparer_algorithmes(graphe, sources=None, avec_floyd=True, tolerance=1e-9):
    # verifie que dijkstra, bellman-ford et floyd-warshall donnent les memes distances
    if sources is None:
        sources = graphe.sommets()
    dist_fw = floyd_warshall(graphe)[0] if avec_floyd else None
    differences = []

    for s in sources:
        d_dij, _ = dijkstra(graphe, s)
        d_bf, _ = bellman_ford(graphe, s)
        for t in graphe.sommets():
            valeurs = {"dijkstra": d_dij[t], "bellman_ford": d_bf[t]}
            if dist_fw is not None:
                valeurs["floyd_warshall"] = dist_fw[s][t]
            ref = valeurs["dijkstra"]
            for nom, val in valeurs.items():
                if val == ref:
                    continue
                if val in (INF, MOINS_INF) or ref in (INF, MOINS_INF) or abs(val - ref) > tolerance:
                    differences.append((s, t, valeurs))
                    break

    return differences
