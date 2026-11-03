from collections import deque


STATUTS_FERMES = {"ferme", "fermé", "fermee", "fermée"}


def arc_ouvert(attributs):
    # un arc "travaux" reste praticable, seul "ferme" bloque
    statut = (attributs or {}).get("statut", "ouvert")
    return str(statut).strip().lower() not in STATUTS_FERMES


def successeurs_ouverts(graphe, u):
    # comme graphe.successeurs mais sans les arcs au statut ferme
    u_id = str(u)
    adj = getattr(graphe, "_adj", None)
    if adj is None:
        return graphe.successeurs(u_id)
    if u_id not in adj:
        raise KeyError(f"Le sommet '{u_id}' n'existe pas dans le graphe.")
    return [(arc["cible"], arc["poids"]) for arc in adj[u_id] if arc_ouvert(arc.get("attributs"))]


def _verifier_source(graphe, source):
    if not graphe.a_sommet(source):
        raise KeyError(f"Le sommet source '{source}' n'existe pas dans le graphe.")
    return str(source)


def casernes_du_graphe(graphe):
    return [s for s in graphe.sommets() if graphe.attributs_sommet(s).get("type") == "caserne"]


# ---------------------------------------------------------------- B1 : DFS


def dfs(graphe, source):
    # version pile du cours : on depile, on marque, on empile les successeurs
    source = _verifier_source(graphe, source)
    visites = set()
    ordre = []
    pred = {source: None}
    pile = [source]

    while pile:
        u = pile.pop()
        if u in visites:
            continue
        visites.add(u)
        ordre.append(u)
        # empile a l'envers pour visiter les voisins dans l'ordre de la liste
        for v, _ in reversed(successeurs_ouverts(graphe, u)):
            if v not in visites:
                pred[v] = u
                pile.append(v)

    pred = {v: p for v, p in pred.items() if v in visites}
    return ordre, pred


# ---------------------------------------------------------------- B2 : BFS


def bfs(graphe, source):
    # dist = nombre d'arcs, inf si non atteint
    source = _verifier_source(graphe, source)
    dist = {s: float("inf") for s in graphe.sommets()}
    pred = {s: None for s in graphe.sommets()}
    dist[source] = 0
    file = deque([source])

    while file:
        u = file.popleft()
        for v, _ in successeurs_ouverts(graphe, u):
            if dist[v] == float("inf"):
                dist[v] = dist[u] + 1
                pred[v] = u
                file.append(v)

    return dist, pred


def chemin_min_arcs(graphe, source, cible):
    from src.graphe import reconstruire_chemin

    _, pred = bfs(graphe, source)
    return reconstruire_chemin(pred, source, cible)


# ---------------------------------------------------------------- B3 : multi-casernes


def accessibilite_multi_sources(graphe, sources=None):
    # toutes les casernes dans la file au depart
    # renvoie {site: (nb_arcs, caserne d'origine)} pour les sites atteints, et pred
    if sources is None:
        sources = casernes_du_graphe(graphe)
    atteints = {}
    pred = {}
    file = deque()

    for s in sources:
        s = _verifier_source(graphe, s)
        if s not in atteints:
            atteints[s] = (0, s)
            pred[s] = None
            file.append(s)

    while file:
        u = file.popleft()
        niveau, origine = atteints[u]
        for v, _ in successeurs_ouverts(graphe, u):
            if v not in atteints:
                atteints[v] = (niveau + 1, origine)
                pred[v] = u
                file.append(v)

    return atteints, pred


# ---------------------------------------------------------------- B4 : circuits


def trouver_circuit(graphe):
    # dfs 3 couleurs iteratif : un arc vers un sommet gris ferme un circuit
    BLANC, GRIS, NOIR = 0, 1, 2
    couleur = {s: BLANC for s in graphe.sommets()}
    parent = {}

    for depart in graphe.sommets():
        if couleur[depart] != BLANC:
            continue
        couleur[depart] = GRIS
        parent[depart] = None
        # pile de (sommet, iterateur sur ses successeurs)
        pile = [(depart, iter(successeurs_ouverts(graphe, depart)))]

        while pile:
            u, it = pile[-1]
            avance = False
            for v, _ in it:
                if couleur[v] == BLANC:
                    couleur[v] = GRIS
                    parent[v] = u
                    pile.append((v, iter(successeurs_ouverts(graphe, v))))
                    avance = True
                    break
                if couleur[v] == GRIS:
                    # remonte de u jusqu'a v pour extraire le circuit
                    circuit = [u]
                    x = u
                    while x != v:
                        x = parent[x]
                        circuit.append(x)
                    circuit.reverse()
                    circuit.append(v)
                    return circuit
            if not avance:
                couleur[u] = NOIR
                pile.pop()

    return None


def contient_circuit(graphe):
    return trouver_circuit(graphe) is not None


# ---------------------------------------------------------------- B5 : isoles


def sites_isoles(graphe):
    # aucun arc entrant ni sortant (arcs fermes ignores)
    a_un_arc = set()
    for u in graphe.sommets():
        succ = successeurs_ouverts(graphe, u)
        if succ:
            a_un_arc.add(u)
        for v, _ in succ:
            a_un_arc.add(v)
    return [s for s in graphe.sommets() if s not in a_un_arc]


def sites_non_atteignables(graphe, sources=None):
    atteints, _ = accessibilite_multi_sources(graphe, sources)
    return [s for s in graphe.sommets() if s not in atteints]


# ---------------------------------------------------------------- B6 : connexite


def _graphe_inverse(graphe):
    inverse = {s: [] for s in graphe.sommets()}
    for u in graphe.sommets():
        for v, _ in successeurs_ouverts(graphe, u):
            inverse[v].append(u)
    return inverse


def composantes_fortement_connexes(graphe):
    # kosaraju : 1er dfs pour l'ordre de fin, 2e dfs sur le graphe inverse
    visites = set()
    ordre_fin = []

    for depart in graphe.sommets():
        if depart in visites:
            continue
        visites.add(depart)
        pile = [(depart, iter(successeurs_ouverts(graphe, depart)))]
        while pile:
            u, it = pile[-1]
            avance = False
            for v, _ in it:
                if v not in visites:
                    visites.add(v)
                    pile.append((v, iter(successeurs_ouverts(graphe, v))))
                    avance = True
                    break
            if not avance:
                ordre_fin.append(u)
                pile.pop()

    inverse = _graphe_inverse(graphe)
    affectes = set()
    composantes = []
    for depart in reversed(ordre_fin):
        if depart in affectes:
            continue
        comp = []
        affectes.add(depart)
        pile = [depart]
        while pile:
            u = pile.pop()
            comp.append(u)
            for v in inverse[u]:
                if v not in affectes:
                    affectes.add(v)
                    pile.append(v)
        composantes.append(sorted(comp))

    return composantes


def composantes_connexes(graphe):
    # connexite simple : on oublie le sens des arcs
    voisins = {s: set() for s in graphe.sommets()}
    for u in graphe.sommets():
        for v, _ in successeurs_ouverts(graphe, u):
            voisins[u].add(v)
            voisins[v].add(u)

    vus = set()
    composantes = []
    for depart in graphe.sommets():
        if depart in vus:
            continue
        vus.add(depart)
        comp = []
        file = deque([depart])
        while file:
            u = file.popleft()
            comp.append(u)
            for v in voisins[u]:
                if v not in vus:
                    vus.add(v)
                    file.append(v)
        composantes.append(sorted(comp))
    return composantes


def est_fortement_connexe(graphe):
    return len(composantes_fortement_connexes(graphe)) <= 1


# ---------------------------------------------------------------- synthese module 1


TYPES_SENSIBLES = ("hopital", "ecole", "telecom")


def diagnostic_accessibilite(graphe, sources=None):
    # regroupe les 3 notions : accessibilite depuis les casernes, connexite, connexite forte
    if sources is None:
        sources = casernes_du_graphe(graphe)
    atteints, _ = accessibilite_multi_sources(graphe, sources)
    non_atteints = [s for s in graphe.sommets() if s not in atteints]

    sensibles = [s for s in graphe.sommets() if graphe.attributs_sommet(s).get("type") in TYPES_SENSIBLES]
    sensibles_atteints = [s for s in sensibles if s in atteints]

    cfc = composantes_fortement_connexes(graphe)
    cc = composantes_connexes(graphe)

    return {
        "casernes": list(sources),
        "nb_sites": graphe.nombre_sommets(),
        "nb_atteignables": len(atteints),
        "non_atteignables": non_atteints,
        "isoles": sites_isoles(graphe),
        "sensibles_total": len(sensibles),
        "sensibles_accessibles": len(sensibles_atteints),
        "sensibles_non_accessibles": [s for s in sensibles if s not in atteints],
        "caserne_par_site": {s: origine for s, (_, origine) in atteints.items()},
        "nb_composantes_connexes": len(cc),
        "nb_cfc": len(cfc),
        "plus_grande_cfc": max((len(c) for c in cfc), default=0),
        "cfc": cfc,
        "circuit_exemple": trouver_circuit(graphe),
    }
