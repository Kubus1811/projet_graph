import copy


class Graphe:
    def __init__(self, oriente=True):
        self.oriente = bool(oriente)
        self._sommets = {}
        # dict: id -> liste de dicts {cible, poids, attributs}
        self._adj = {}

    def ajouter_sommet(self, id, **attributs):
        s_id = str(id)
        if s_id not in self._sommets:
            self._sommets[s_id] = dict(attributs)
            self._adj[s_id] = []
        else:
            self._sommets[s_id].update(attributs)

    def ajouter_arc(self, u, v, poids, **attributs):
        u_id = str(u)
        v_id = str(v)
        poids_val = float(poids)

        if u_id not in self._sommets:
            self.ajouter_sommet(u_id)
        if v_id not in self._sommets:
            self.ajouter_sommet(v_id)

        self._inserer_arc_unidirectionnel(u_id, v_id, poids_val, dict(attributs))

        # si non oriente on ajoute l'arc dans les deux sens
        if not self.oriente and u_id != v_id:
            self._inserer_arc_unidirectionnel(v_id, u_id, poids_val, dict(attributs))

    def _inserer_arc_unidirectionnel(self, u, v, poids, attributs):
        for arc in self._adj[u]:
            if arc["cible"] == v:
                arc["poids"] = poids
                arc["attributs"] = attributs
                return
        self._adj[u].append({
            "cible": v,
            "poids": poids,
            "attributs": attributs,
        })

    def successeurs(self, u):
        u_id = str(u)
        if u_id not in self._sommets:
            raise KeyError(f"Le sommet '{u_id}' n'existe pas dans le graphe.")
        return [(arc["cible"], arc["poids"]) for arc in self._adj[u_id]]

    def voisins(self, u):
        return [cible for cible, _ in self.successeurs(u)]

    def sommets(self):
        return list(self._sommets.keys())

    def arcs(self, uniques_si_non_oriente=True):
        # en non oriente on renvoie chaque arete une seule fois pour kruskal
        resultat = []
        if not self.oriente and uniques_si_non_oriente:
            vus = set()
            for u, liste_adj in self._adj.items():
                for arc in liste_adj:
                    v = arc["cible"]
                    cle = (u, v) if u <= v else (v, u)
                    if cle not in vus:
                        vus.add(cle)
                        resultat.append((u, v, arc["poids"]))
        else:
            for u, liste_adj in self._adj.items():
                for arc in liste_adj:
                    resultat.append((u, arc["cible"], arc["poids"]))
        return resultat

    def degre(self, u):
        u_id = str(u)
        if u_id not in self._adj:
            raise KeyError(f"Le sommet '{u_id}' n'existe pas.")
        return len(self._adj[u_id])

    def a_sommet(self, u):
        return str(u) in self._sommets

    def a_arc(self, u, v):
        u_id = str(u)
        v_id = str(v)
        if u_id not in self._adj:
            return False
        return any(arc["cible"] == v_id for arc in self._adj[u_id])

    def poids_arc(self, u, v):
        u_id = str(u)
        v_id = str(v)
        if u_id not in self._adj:
            return None
        for arc in self._adj[u_id]:
            if arc["cible"] == v_id:
                return arc["poids"]
        return None

    def modifier_poids_arc(self, u, v, nouveau_poids):
        u_id = str(u)
        v_id = str(v)
        poids_val = float(nouveau_poids)
        trouve = False

        if u_id in self._adj:
            for arc in self._adj[u_id]:
                if arc["cible"] == v_id:
                    arc["poids"] = poids_val
                    trouve = True
                    break

        if not self.oriente and v_id in self._adj:
            for arc in self._adj[v_id]:
                if arc["cible"] == u_id:
                    arc["poids"] = poids_val
                    trouve = True
                    break

        return trouve

    def supprimer_arc(self, u, v):
        u_id = str(u)
        v_id = str(v)
        supprime = False

        if u_id in self._adj:
            avant = len(self._adj[u_id])
            self._adj[u_id] = [arc for arc in self._adj[u_id] if arc["cible"] != v_id]
            if len(self._adj[u_id]) < avant:
                supprime = True

        if not self.oriente and v_id in self._adj:
            avant = len(self._adj[v_id])
            self._adj[v_id] = [arc for arc in self._adj[v_id] if arc["cible"] != u_id]
            if len(self._adj[v_id]) < avant:
                supprime = True

        return supprime

    def attributs_sommet(self, u):
        u_id = str(u)
        if u_id not in self._sommets:
            raise KeyError(f"Le sommet '{u_id}' n'existe pas.")
        return dict(self._sommets[u_id])

    def attributs_arc(self, u, v):
        u_id = str(u)
        v_id = str(v)
        if u_id not in self._adj:
            return None
        for arc in self._adj[u_id]:
            if arc["cible"] == v_id:
                return dict(arc["attributs"])
        return None

    def copie(self):
        # deepcopy obligatoire pour pas impacter le graphe de base
        g_copie = Graphe(oriente=self.oriente)
        g_copie._sommets = copy.deepcopy(self._sommets)
        g_copie._adj = copy.deepcopy(self._adj)
        return g_copie

    def nombre_sommets(self):
        return len(self._sommets)

    def nombre_arcs(self):
        return len(self.arcs(uniques_si_non_oriente=True))

    def __len__(self):
        return self.nombre_sommets()

    def __contains__(self, u):
        return self.a_sommet(u)

    def __repr__(self):
        t = "oriente" if self.oriente else "non oriente"
        return f"Graphe({t}, {len(self._sommets)} sommets, {self.nombre_arcs()} arcs)"


def reconstruire_chemin(pred, source, cible):
    # remonte les predecesseurs de la cible vers la source
    s = str(source)
    c = str(cible)

    if s == c:
        return [s]

    if c not in pred or pred[c] is None:
        return None

    chemin = []
    courant = c
    vus = set()

    while courant is not None:
        # securite si cycle dans pred
        if courant in vus:
            return None
        vus.add(courant)
        chemin.append(courant)
        if courant == s:
            break
        courant = pred.get(courant)

    if chemin[-1] != s:
        return None

    chemin.reverse()
    return chemin
