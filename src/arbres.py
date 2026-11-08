import heapq
import math
from collections import deque


class UnionFind:
    def __init__(self, elements=()):
        self._parent = {}
        self._rang = {}
        self.nombre_ensembles = 0
        for e in elements:
            self.ajouter(e)

    def ajouter(self, e):
        # chaque nouvel element forme un ensemble a lui seul
        if e not in self._parent:
            self._parent[e] = e
            self._rang[e] = 0
            self.nombre_ensembles += 1

    def trouver(self, e):
        # iteratif pour eviter la limite de recursion de python
        racine = e
        while self._parent[racine] != racine:
            racine = self._parent[racine]

        # compression de chemin : tout le chemin pointe vers la racine
        while self._parent[e] != racine:
            suivant = self._parent[e]
            self._parent[e] = racine
            e = suivant

        return racine

    def unir(self, a, b):
        # renvoie False si deja ensemble : pour kruskal cette arete ferait un cycle
        racine_a = self.trouver(a)
        racine_b = self.trouver(b)
        if racine_a == racine_b:
            return False

        # union par rang : l'arbre le moins haut passe sous l'autre
        if self._rang[racine_a] < self._rang[racine_b]:
            racine_a, racine_b = racine_b, racine_a
        self._parent[racine_b] = racine_a
        if self._rang[racine_a] == self._rang[racine_b]:
            self._rang[racine_a] += 1

        self.nombre_ensembles -= 1
        return True

    def meme_ensemble(self, a, b):
        return self.trouver(a) == self.trouver(b)


def _indisponibles(graphe):
    # un troncon ferme ou en travaux ne peut pas porter la fibre
    # un seul passage sur les arcs, puis des tests en O(1)
    return {
        (u, arc["cible"])
        for u, arcs in graphe._adj.items()
        for arc in arcs
        if arc["attributs"].get("statut", "ouvert") != "ouvert"
    }


def _aretes_triees(graphe):
    # (u, v) range dans l'ordre pour que le resultat ne depende pas du fichier
    indisponibles = _indisponibles(graphe)
    aretes = []
    for u, v, cout in graphe.arcs():
        if (u, v) in indisponibles:
            continue
        if u > v:
            u, v = v, u
        aretes.append((cout, u, v))
    aretes.sort()
    return aretes


def kruskal(graphe):
    if graphe.oriente:
        raise ValueError("Kruskal demande un graphe non oriente.")

    uf = UnionFind(graphe.sommets())
    aretes_choisies = []
    cout_total = 0.0

    for cout, u, v in _aretes_triees(graphe):
        # unir renvoie False si l'arete ferait un cycle
        if uf.unir(u, v):
            aretes_choisies.append((u, v, cout))
            cout_total += cout

    # s'il reste plusieurs ensembles le graphe n'est pas connexe : on obtient une foret
    return {
        "aretes": aretes_choisies,
        "cout_total": cout_total,
        "nb_composantes": uf.nombre_ensembles,
    }


def prim(graphe):
    if graphe.oriente:
        raise ValueError("Prim demande un graphe non oriente.")

    indisponibles = _indisponibles(graphe)
    visites = set()
    aretes_choisies = []
    cout_total = 0.0
    nb_composantes = 0

    # relance depuis chaque sommet non visite pour obtenir une foret si non connexe
    # sommets tries pour que le resultat ne depende pas du fichier
    for depart in sorted(graphe.sommets()):
        if depart in visites:
            continue

        nb_composantes += 1
        visites.add(depart)
        tas = [(cout, depart, v) for v, cout in graphe.successeurs(depart) if (depart, v) not in indisponibles]
        heapq.heapify(tas)

        while tas:
            cout, u, v = heapq.heappop(tas)
            # suppression paresseuse : v a pu etre atteint entre temps par moins cher
            if v in visites:
                continue

            visites.add(v)
            aretes_choisies.append((u, v, cout) if u < v else (v, u, cout))
            cout_total += cout

            for w, cout_vw in graphe.successeurs(v):
                if w not in visites and (v, w) not in indisponibles:
                    heapq.heappush(tas, (cout_vw, v, w))

    return {
        "aretes": aretes_choisies,
        "cout_total": cout_total,
        "nb_composantes": nb_composantes,
    }


def trouver_composantes(graphe):
    if graphe.oriente:
        raise ValueError("Les composantes connexes demandent un graphe non oriente.")

    # bfs relance depuis chaque sommet non visite : O(|V| + |E|)
    indisponibles = _indisponibles(graphe)
    visites = set()
    composantes = []

    for depart in graphe.sommets():
        if depart in visites:
            continue

        visites.add(depart)
        composante = []
        file = deque([depart])
        while file:
            u = file.popleft()
            composante.append(u)
            for v, _ in graphe.successeurs(u):
                if v not in visites and (u, v) not in indisponibles:
                    visites.add(v)
                    file.append(v)

        composantes.append(sorted(composante))

    # la plus grande d'abord : les suivantes sont les parties non raccordees
    composantes.sort(key=lambda c: (-len(c), c[0]))
    return composantes


def comparer_kruskal_prim(graphe):
    res_kruskal = kruskal(graphe)
    res_prim = prim(graphe)

    aretes_k = set(res_kruskal["aretes"])
    aretes_p = set(res_prim["aretes"])

    return {
        "kruskal": res_kruskal,
        "prim": res_prim,
        # isclose car les couts sont additionnes dans un ordre different
        "meme_cout": math.isclose(res_kruskal["cout_total"], res_prim["cout_total"], abs_tol=1e-9),
        "meme_arbre": aretes_k == aretes_p,
        "seulement_kruskal": sorted(aretes_k - aretes_p),
        "seulement_prim": sorted(aretes_p - aretes_k),
    }


def formater_comparaison_acm(graphe):
    comp = comparer_kruskal_prim(graphe)
    composantes = trouver_composantes(graphe)
    lignes = []

    for nom, cle in (("Kruskal", "kruskal"), ("Prim", "prim")):
        res = comp[cle]
        lignes.append(
            f"{nom:<8}: {len(res['aretes'])} troncons, cout total {res['cout_total']:.2f}, "
            f"{res['nb_composantes']} composante(s)"
        )

    lignes.append(f"Meme cout total : {'oui' if comp['meme_cout'] else 'NON'}")

    if comp["meme_arbre"]:
        lignes.append("Meme arbre : oui")
    else:
        lignes.append(f"Meme arbre : non ({len(comp['seulement_kruskal'])} troncon(s) different(s))")
        for u, v, cout in comp["seulement_kruskal"]:
            lignes.append(f"  seulement Kruskal : {u} - {v} ({cout:.2f})")
        for u, v, cout in comp["seulement_prim"]:
            lignes.append(f"  seulement Prim    : {u} - {v} ({cout:.2f})")

    lignes.append("")
    lignes.append("Troncons choisis (Kruskal) :")
    for u, v, cout in comp["kruskal"]["aretes"]:
        lignes.append(f"  {u} - {v} : {cout:.2f}")

    lignes.append("")
    if len(composantes) <= 1:
        lignes.append("Composantes non raccordees : aucune")
    else:
        lignes.append(f"Composantes non raccordees : {len(composantes) - 1}")
        for composante in composantes[1:]:
            lignes.append(f"  {composante}")

    return "\n".join(lignes)


def _sommets_atteints(adjacence, depart):
    visites = {depart}
    file = deque([depart])
    while file:
        u = file.popleft()
        for v in adjacence[u]:
            if v not in visites:
                visites.add(v)
                file.append(v)
    return visites


def analyser_panne(graphe, u, v):
    if graphe.oriente:
        raise ValueError("L'analyse de panne demande un graphe non oriente.")

    u, v = str(u), str(v)
    cout_panne = graphe.poids_arc(u, v)
    if cout_panne is None:
        raise ValueError(f"Le troncon {u} - {v} n'existe pas dans le reseau de fibre.")
    if u > v:
        u, v = v, u

    arbre = kruskal(graphe)
    resultat = {
        "panne": (u, v, cout_panne),
        "dans_arbre": (u, v, cout_panne) in arbre["aretes"],
        "cote_1": [],
        "cote_2": [],
        "raccordement": None,
        "raccordable": True,
        "cout_reparation": 0.0,
        "cout_arbre_avant": arbre["cout_total"],
        "cout_arbre_apres": arbre["cout_total"],
        "nb_composantes_avant": arbre["nb_composantes"],
        "nb_composantes_panne": arbre["nb_composantes"],
    }

    # hors de l'arbre le troncon n'etait pas utilise : la panne ne coupe rien
    if not resultat["dans_arbre"]:
        return resultat

    # sans le troncon, son arbre se coupe en exactement 2 cotes
    adjacence = {s: [] for s in graphe.sommets()}
    for a, b, _ in arbre["aretes"]:
        if (a, b) != (u, v):
            adjacence[a].append(b)
            adjacence[b].append(a)
    cote_1 = _sommets_atteints(adjacence, u)
    cote_2 = _sommets_atteints(adjacence, v)

    resultat["cote_1"] = sorted(cote_1)
    resultat["cote_2"] = sorted(cote_2)
    resultat["nb_composantes_panne"] = arbre["nb_composantes"] + 1
    resultat["cout_arbre_apres"] = arbre["cout_total"] - cout_panne
    resultat["raccordable"] = False

    # on cherche dans le graphe initial : aretes triees donc la premiere trouvee est la moins chere
    for cout, a, b in _aretes_triees(graphe):
        if (a, b) == (u, v):
            continue
        if (a in cote_1 and b in cote_2) or (a in cote_2 and b in cote_1):
            resultat["raccordement"] = (a, b, cout)
            resultat["raccordable"] = True
            resultat["cout_reparation"] = cout
            resultat["cout_arbre_apres"] += cout
            break

    return resultat


def formater_panne(resultat):
    u, v, cout = resultat["panne"]
    lignes = [f"Panne du troncon {u} - {v} (cout {cout:.2f})"]

    if not resultat["dans_arbre"]:
        lignes.append("Ce troncon n'est pas dans l'arbre couvrant : aucune coupure, aucune reparation.")
        return "\n".join(lignes)

    lignes.append(f"Composantes apres la panne : {resultat['nb_composantes_panne']}")
    lignes.append(f"  Cote {u} : {resultat['cote_1']}")
    lignes.append(f"  Cote {v} : {resultat['cote_2']}")

    if resultat["raccordable"]:
        a, b, cout_r = resultat["raccordement"]
        lignes.append(f"Raccordement le moins cher : {a} - {b} (cout {cout_r:.2f})")
    else:
        lignes.append("Raccordement impossible : aucun troncon disponible ne relie les deux cotes.")

    lignes.append(f"Cout de la reparation : {resultat['cout_reparation']:.2f}")
    lignes.append(f"Cout de l'arbre : {resultat['cout_arbre_avant']:.2f} -> {resultat['cout_arbre_apres']:.2f}")
    return "\n".join(lignes)


def reparer_pannes(graphe, pannes):
    if graphe.oriente:
        raise ValueError("La reparation demande un graphe non oriente.")

    coupes = set()
    for u, v in pannes:
        u, v = str(u), str(v)
        if not graphe.a_arc(u, v):
            raise ValueError(f"Le troncon {u} - {v} n'existe pas dans le reseau de fibre.")
        coupes.add((u, v) if u < v else (v, u))

    arbre = kruskal(graphe)
    restantes = [a for a in arbre["aretes"] if (a[0], a[1]) not in coupes]
    coupees = [a for a in arbre["aretes"] if (a[0], a[1]) in coupes]

    uf = UnionFind(graphe.sommets())
    for u, v, _ in restantes:
        uf.unir(u, v)
    nb_composantes_panne = uf.nombre_ensembles

    # comme kruskal, mais en partant de ce qui reste de l'arbre : plusieurs pannes a la fois sont gerees
    raccordements = []
    cout_reparation = 0.0
    for cout, a, b in _aretes_triees(graphe):
        if (a, b) in coupes:
            continue
        if uf.unir(a, b):
            raccordements.append((a, b, cout))
            cout_reparation += cout

    return {
        "coupees": coupees,
        "restantes": restantes,
        "raccordements": raccordements,
        "cout_reparation": cout_reparation,
        "nb_composantes_avant": arbre["nb_composantes"],
        "nb_composantes_panne": nb_composantes_panne,
        "nb_composantes_apres": uf.nombre_ensembles,
        "cout_arbre_avant": arbre["cout_total"],
        "cout_arbre_apres": sum(a[2] for a in restantes) + cout_reparation,
    }


def formater_pannes_simultanees(resultat):
    lignes = [f"Troncons de l'arbre coupes : {len(resultat['coupees'])}"]
    for u, v, cout in resultat["coupees"]:
        lignes.append(f"  {u} - {v} ({cout:.2f})")

    lignes.append(f"Composantes apres les pannes : {resultat['nb_composantes_panne']}")
    if resultat["raccordements"]:
        lignes.append("Raccordements les moins chers :")
        for u, v, cout in resultat["raccordements"]:
            lignes.append(f"  {u} - {v} ({cout:.2f})")
    if resultat["nb_composantes_apres"] > resultat["nb_composantes_avant"]:
        lignes.append(f"Raccordement incomplet : il reste {resultat['nb_composantes_apres']} composantes.")

    lignes.append(f"Cout de la reparation : {resultat['cout_reparation']:.2f}")
    lignes.append(f"Cout de l'arbre : {resultat['cout_arbre_avant']:.2f} -> {resultat['cout_arbre_apres']:.2f}")
    return "\n".join(lignes)


def kruskal_etapes(graphe):
    # meme parcours que kruskal, en gardant chaque decision pour pouvoir la montrer
    if graphe.oriente:
        raise ValueError("Kruskal demande un graphe non oriente.")

    uf = UnionFind(graphe.sommets())
    return [
        {"u": u, "v": v, "cout": cout, "gardee": uf.unir(u, v)}
        for cout, u, v in _aretes_triees(graphe)
    ]
