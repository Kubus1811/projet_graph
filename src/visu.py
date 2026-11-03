import argparse
import math
import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# permet aussi de lancer "python src/visu.py" (bouton Run de VS Code) et pas seulement "python -m src.visu"
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

try:
    import pygame
    from pygame.math import Vector2
except ImportError:
    sys.exit(f"pygame n'est pas installe pour cet interpreteur ({sys.executable}).\n"
             f"Installer avec : \"{sys.executable}\" -m pip install pygame-ce")

from src.io_donnees import charger_jeu_donnees
from src.indicateurs import appliquer_scenario
from src.parcours import arc_ouvert, accessibilite_multi_sources, composantes_fortement_connexes, casernes_du_graphe
from src import chemins


LARGEUR, HAUTEUR = 1280, 800
PANNEAU = 340
MARGE = 40

FOND = (18, 20, 28)
COUL_ARC = (70, 76, 95)
COUL_TEXTE = (225, 228, 235)
COUL_GRIS = (140, 145, 160)
COUL_CHEMIN = (0, 220, 140)
COUL_SOURCE = (60, 160, 255)
COUL_CIBLE = (255, 200, 40)
COUL_FERME = (235, 60, 60)
COUL_MODIFIE = (255, 150, 40)
COUL_VEHICULE = (255, 255, 255)

COUL_TYPES = {
    "caserne": (230, 70, 60),
    "hopital": (90, 210, 230),
    "ecole": (240, 210, 70),
    "telecom": (180, 110, 240),
    "quartier": (120, 125, 140),
}

# pas de rouge : il est reserve aux sites non atteignables et aux routes fermees
PALETTE = [
    (80, 170, 240), (110, 210, 110), (240, 190, 60), (190, 120, 240), (60, 210, 200),
    (240, 130, 190), (170, 200, 80), (250, 150, 70), (130, 140, 250), (200, 200, 200),
]

ALGOS = ["dijkstra", "bellman_ford", "floyd_warshall"]
MODES = ["chemin", "accessibilite", "cfc", "itineraires"]
VITESSE_VEHICULE = 220.0  # pixels par seconde


# ---------------------------------------------------------------- geometrie vectorielle


def projeter_sites(sites, largeur, hauteur, marge=MARGE):
    # lon/lat -> pixels, la longitude est corrigee par cos(lat) pour garder les proportions
    if not sites:
        return {}
    lat_moy = sum(a["latitude"] for a in sites.values()) / len(sites)
    k = math.cos(math.radians(lat_moy))
    bruts = {s: Vector2(a["longitude"] * k, -a["latitude"]) for s, a in sites.items()}

    mini = Vector2(min(p.x for p in bruts.values()), min(p.y for p in bruts.values()))
    maxi = Vector2(max(p.x for p in bruts.values()), max(p.y for p in bruts.values()))
    etendue = maxi - mini
    zone = Vector2(largeur - 2 * marge, hauteur - 2 * marge)
    echelle = min(zone.x / etendue.x if etendue.x else math.inf,
                  zone.y / etendue.y if etendue.y else math.inf)
    if echelle == math.inf:
        echelle = 1.0
    # centre le dessin dans la zone
    decalage = Vector2(marge, marge) + (zone - etendue * echelle) / 2
    return {s: decalage + (p - mini) * echelle for s, p in bruts.items()}


def geometrie_fleche(a, b, rayon, decalage=0.0, taille=8.0):
    # renvoie (debut, fin, triangle) d'un arc a -> b raccourci du rayon des sommets
    # decalage : translation perpendiculaire pour separer u->v et v->u
    d = b - a
    if d.length() <= 2 * rayon:
        return None
    u = d.normalize()
    n = Vector2(-u.y, u.x)
    debut = a + u * rayon + n * decalage
    fin = b - u * rayon + n * decalage
    triangle = [fin, fin - u * taille + n * taille * 0.45, fin - u * taille - n * taille * 0.45]
    return debut, fin, triangle


def position_poids(a, b, ecart=10.0):
    # milieu de l'arc a -> b pousse sur sa gauche (normale) :
    # u->v et v->u ont des normales opposees donc leurs deux poids ne se chevauchent pas
    d = b - a
    if d.length() == 0:
        return Vector2(a)
    u = d.normalize()
    return a.lerp(b, 0.5) + Vector2(-u.y, u.x) * ecart


def texte_poids(poids):
    # 4.0 -> "4", 3.9 -> "3.9"
    return f"{poids:g}"


def point_sur_polyligne(points, distance):
    # position a une distance donnee le long du chemin (interpolation lineaire)
    if not points:
        return None
    for a, b in zip(points, points[1:]):
        seg = a.distance_to(b)
        if distance <= seg:
            return a.lerp(b, distance / seg) if seg else Vector2(a)
        distance -= seg
    return Vector2(points[-1])


def longueur_polyligne(points):
    return sum(a.distance_to(b) for a, b in zip(points, points[1:]))


# ---------------------------------------------------------------- visualiseur


class Visualiseur:
    def __init__(self, donnees, largeur=LARGEUR, hauteur=HAUTEUR):
        self.donnees = donnees
        self.largeur, self.hauteur = largeur, hauteur
        self.g_ref = donnees["graphe_routes"]
        self.sites = donnees["sites"]
        self.casernes = casernes_du_graphe(self.g_ref)

        self.pos_monde = projeter_sites(self.sites, largeur - PANNEAU, hauteur)
        self.zoom = 1.0
        self.pan = Vector2(0, 0)

        n = self.g_ref.nombre_sommets()
        self.rayon_base = 9 if n <= 30 else (6 if n <= 200 else 3)

        # scenarios qui touchent les routes, None = situation normale
        noms = []
        for r in donnees["scenarios"]:
            if r["action"] != "fermer_fibre" and r["scenario"] not in noms:
                noms.append(r["scenario"])
        self.scenarios = [None] + noms
        self.i_scenario = 0
        self.g = self.g_ref

        self.algo = "dijkstra"
        self.mode = "chemin"
        self.source = None
        self.cible = None
        self.survol = None
        self.aide = True
        self.afficher_poids = False
        self.poids_caches = 0
        self.message = ""

        self.itineraire = None
        self.duree_ref = None
        self.points_chemin = []
        self.t_vehicule = 0.0
        self.exploration = []
        self.t_exploration = None
        self._cache_fw = {}
        self._cache_couleurs = None
        self.fond = None

    # ------------------------------------------------------------ transformations

    def ecran(self, s):
        return self.pan + self.pos_monde[s] * self.zoom

    def rayon(self):
        return max(2, self.rayon_base * min(self.zoom, 3) ** 0.5)

    def sommet_sous(self, pos):
        pos = Vector2(pos)
        meilleur, d_min = None, self.rayon() + 6
        for s in self.pos_monde:
            d = pos.distance_to(self.ecran(s))
            if d < d_min:
                meilleur, d_min = s, d
        return meilleur

    def zoomer(self, facteur, centre):
        centre = Vector2(centre)
        nouveau = max(0.3, min(12.0, self.zoom * facteur))
        # le point sous la souris reste fixe
        self.pan = centre - (centre - self.pan) * (nouveau / self.zoom)
        self.zoom = nouveau
        self.invalider()

    def invalider(self):
        self.fond = None
        self.points_chemin = [self.ecran(s) for s in (self.itineraire or {}).get("chemin") or []]

    # ------------------------------------------------------------ etat

    def changer_scenario(self, i):
        self.i_scenario = i % len(self.scenarios)
        nom = self.scenarios[self.i_scenario]
        self.g = self.g_ref if nom is None else appliquer_scenario(self.g_ref, self.donnees["scenarios"], nom)
        self._cache_couleurs = None
        self.recalculer()

    def changer_mode(self, mode):
        self.mode = mode
        self._cache_couleurs = None
        self.invalider()

    def _plus_courts_chemins(self, g, source, cle):
        if self.algo == "dijkstra":
            return chemins.dijkstra(g, source)
        if self.algo == "bellman_ford":
            return chemins.bellman_ford(g, source)
        if g.nombre_sommets() > 400:
            self.message = "Floyd-Warshall limite a 400 sommets : Dijkstra utilise."
            return chemins.dijkstra(g, source)
        if cle not in self._cache_fw:
            self._cache_fw[cle] = chemins.floyd_warshall(g)
        dist, pred = self._cache_fw[cle]
        return dist[source], pred[source]

    def recalculer(self):
        self.message = ""
        self.itineraire = None
        self.duree_ref = None
        self.exploration = []
        self.t_exploration = None
        if self.source is not None:
            try:
                dist, pred = self._plus_courts_chemins(self.g, self.source, self.i_scenario)
            except chemins.PoidsNegatifErreur:
                self.message = "poids negatifs : Bellman-Ford utilise"
                dist, pred = chemins.bellman_ford(self.g, self.source)
            # ordre de visite de Dijkstra = distances croissantes
            atteints = [s for s, d in dist.items() if d != math.inf]
            self.exploration = sorted(atteints, key=lambda s: (dist[s], s))
            self.pred_exploration = pred
            if self.cible is not None:
                self.itineraire = chemins.decrire_itineraire(self.g, dist, pred, self.source, self.cible)
                d_ref, _ = chemins.bellman_ford(self.g_ref, self.source)
                self.duree_ref = d_ref[self.cible]
        self.t_vehicule = 0.0
        self.invalider()

    # ------------------------------------------------------------ couleurs par mode

    def couleurs_sommets(self):
        if self._cache_couleurs is not None:
            return self._cache_couleurs
        couleurs = {}
        if self.mode == "accessibilite":
            atteints, _ = accessibilite_multi_sources(self.g, self.casernes)
            idx = {c: i for i, c in enumerate(self.casernes)}
            for s in self.pos_monde:
                if s in atteints:
                    couleurs[s] = PALETTE[idx[atteints[s][1]] % len(PALETTE)]
                else:
                    couleurs[s] = COUL_FERME
        elif self.mode == "cfc":
            cfc = sorted(composantes_fortement_connexes(self.g), key=len, reverse=True)
            for i, comp in enumerate(cfc):
                for s in comp:
                    couleurs[s] = PALETTE[i % len(PALETTE)] if i < len(PALETTE) else COUL_FERME
        else:
            for s, a in self.sites.items():
                couleurs[s] = COUL_TYPES.get(a.get("type"), COUL_GRIS)
        self._cache_couleurs = couleurs
        return couleurs

    # ------------------------------------------------------------ dessin

    def _dessiner_arc(self, surf, u, v, couleur, epaisseur=1, pointille=False):
        a, b = self.ecran(u), self.ecran(v)
        decalage = 2.5 if self.g_ref.a_arc(v, u) else 0.0
        geo = geometrie_fleche(a, b, self.rayon(), decalage, taille=4 + 2 * epaisseur)
        if geo is None:
            return
        debut, fin, triangle = geo
        if pointille:
            total = debut.distance_to(fin)
            pas = 8
            for k in range(0, int(total), pas * 2):
                p1 = debut.lerp(fin, k / total)
                p2 = debut.lerp(fin, min(1.0, (k + pas) / total))
                pygame.draw.line(surf, couleur, p1, p2, epaisseur)
            milieu = debut.lerp(fin, 0.5)
            c = 5
            pygame.draw.line(surf, couleur, milieu + Vector2(-c, -c), milieu + Vector2(c, c), 2)
            pygame.draw.line(surf, couleur, milieu + Vector2(-c, c), milieu + Vector2(c, -c), 2)
        else:
            pygame.draw.line(surf, couleur, debut, fin, epaisseur)
            pygame.draw.polygon(surf, couleur, triangle)

    def _dessiner_poids(self, surf, u, v, poids, couleur, police, force=False):
        a, b = self.ecran(u), self.ecran(v)
        # arc trop court a l'ecran : on n'ecrit pas, sinon c'est illisible
        if not force and a.distance_to(b) < 45:
            self.poids_caches += 1
            return
        img = police.render(texte_poids(poids), True, couleur)
        centre = position_poids(a, b, ecart=9 + img.get_height() / 2)
        rect = img.get_rect(center=(round(centre.x), round(centre.y)))
        pygame.draw.rect(surf, FOND, rect.inflate(4, 2), border_radius=3)
        surf.blit(img, rect)

    def construire_fond(self):
        surf = pygame.Surface((self.largeur - PANNEAU, self.hauteur))
        surf.fill(FOND)

        # arcs de la situation courante, puis ceux fermes / modifies par le scenario
        for u, v, poids in self.g.arcs():
            attrs = self.g.attributs_arc(u, v) or {}
            if not arc_ouvert(attrs):
                continue
            p_ref = self.g_ref.poids_arc(u, v)
            couleur = COUL_MODIFIE if (p_ref is not None and abs(p_ref - poids) > 1e-9) else COUL_ARC
            self._dessiner_arc(surf, u, v, couleur)
        for u, v, _ in self.g_ref.arcs():
            attrs = self.g.attributs_arc(u, v)
            if attrs is None or not arc_ouvert(attrs):
                self._dessiner_arc(surf, u, v, COUL_FERME, 2, pointille=True)

        if self.mode == "itineraires":
            its = chemins.itineraires_demandes(self.g, self.donnees["demandes"], self.casernes)
            idx = {c: i for i, c in enumerate(self.casernes)}
            for it in its:
                if it["chemin"]:
                    coul = PALETTE[idx[it["caserne"]] % len(PALETTE)]
                    for u, v in zip(it["chemin"], it["chemin"][1:]):
                        self._dessiner_arc(surf, u, v, coul, 3)

        couleurs = self.couleurs_sommets()
        r = self.rayon()
        for s in self.pos_monde:
            p = self.ecran(s)
            pygame.draw.circle(surf, couleurs.get(s, COUL_GRIS), p, r)
            if self.sites[s].get("type") == "caserne":
                pygame.draw.circle(surf, COUL_TEXTE, p, r + 2, 1)

        if self.mode == "itineraires":
            for d in self.donnees["demandes"]:
                if d["origine"] in self.pos_monde:
                    pygame.draw.circle(surf, COUL_CIBLE, self.ecran(d["origine"]), r + 4, 2)

        # poids des arcs (= duree en minutes dans le scenario courant)
        self.poids_caches = 0
        if self.afficher_poids:
            police_p = pygame.font.SysFont("consolas", 12)
            for u, v, poids in self.g.arcs():
                if not arc_ouvert(self.g.attributs_arc(u, v) or {}):
                    continue
                p_ref = self.g_ref.poids_arc(u, v)
                couleur = COUL_MODIFIE if (p_ref is not None and abs(p_ref - poids) > 1e-9) else COUL_GRIS
                self._dessiner_poids(surf, u, v, poids, couleur, police_p)

        # etiquettes seulement si les sommets sont assez gros (petit graphe ou zoom)
        if r >= 7:
            police = pygame.font.SysFont("consolas", 12)
            for s in self.pos_monde:
                img = police.render(s, True, COUL_TEXTE)
                surf.blit(img, self.ecran(s) + Vector2(r + 2, -r - 10))
        self.fond = surf

    def dessiner(self, surf, dt=0.0):
        if self.fond is None:
            self.construire_fond()
        surf.fill(FOND)
        surf.blit(self.fond, (0, 0))
        r = self.rayon()

        # animation de l'exploration (sommets fixes dans l'ordre de Dijkstra)
        if self.t_exploration is not None:
            self.t_exploration += dt
            k = int(self.t_exploration * max(8, len(self.exploration) / 4))
            for s in self.exploration[:k]:
                p = self.pred_exploration.get(s)
                if p is not None:
                    pygame.draw.line(surf, COUL_SOURCE, self.ecran(p), self.ecran(s), 2)
                pygame.draw.circle(surf, COUL_SOURCE, self.ecran(s), r + 1)
            if k >= len(self.exploration) + 15:
                self.t_exploration = None

        # chemin et vehicule qui le parcourt
        if self.points_chemin and len(self.points_chemin) > 1:
            it = self.itineraire
            for u, v in zip(it["chemin"], it["chemin"][1:]):
                self._dessiner_arc(surf, u, v, COUL_CHEMIN, 4)
            if self.afficher_poids:
                police_p = pygame.font.SysFont("consolas", 14, bold=True)
                for u, v in zip(it["chemin"], it["chemin"][1:]):
                    self._dessiner_poids(surf, u, v, self.g.poids_arc(u, v), COUL_CHEMIN, police_p, force=True)
            longueur = longueur_polyligne(self.points_chemin)
            self.t_vehicule = (self.t_vehicule + dt * VITESSE_VEHICULE) % (longueur + 60)
            pos = point_sur_polyligne(self.points_chemin, min(self.t_vehicule, longueur))
            pygame.draw.circle(surf, COUL_VEHICULE, pos, max(4, r * 0.8))
            pygame.draw.circle(surf, COUL_FERME, pos, max(4, r * 0.8), 2)

        if self.source is not None:
            pygame.draw.circle(surf, COUL_SOURCE, self.ecran(self.source), r + 5, 3)
        if self.cible is not None:
            pygame.draw.circle(surf, COUL_CIBLE, self.ecran(self.cible), r + 5, 3)

        self.dessiner_panneau(surf)
        if self.survol is not None:
            self.dessiner_infobulle(surf, self.survol)

    def dessiner_infobulle(self, surf, s):
        police = pygame.font.SysFont("consolas", 14)
        a = self.sites[s]
        txt = f"{s} - {a.get('nom', '')} ({a.get('type', '')})"
        img = police.render(txt, True, COUL_TEXTE)
        p = self.ecran(s) + Vector2(12, 12)
        p.x = min(p.x, self.largeur - PANNEAU - img.get_width() - 8)
        fond = pygame.Rect(p.x - 4, p.y - 2, img.get_width() + 8, img.get_height() + 4)
        pygame.draw.rect(surf, (40, 44, 58), fond, border_radius=4)
        surf.blit(img, p)

    def lignes_panneau(self):
        nom_sc = self.scenarios[self.i_scenario] or "situation normale"
        lignes = [
            ("NOVAPOLIS - routes", COUL_TEXTE),
            (f"{self.g.nombre_sommets()} sites, {self.g.nombre_arcs()} arcs", COUL_GRIS),
            ("", None),
            (f"Scenario : {nom_sc}", COUL_MODIFIE if self.i_scenario else COUL_TEXTE),
            (f"Algorithme : {self.algo}", COUL_TEXTE),
            (f"Mode : {self.mode}", COUL_TEXTE),
            (f"Poids (W) : {'affiches (minutes)' if self.afficher_poids else 'caches'}", COUL_TEXTE),
            ("", None),
        ]
        if self.source:
            lignes.append((f"Source : {self.source}", COUL_SOURCE))
        if self.cible:
            lignes.append((f"Cible  : {self.cible}", COUL_CIBLE))
        it = self.itineraire
        if it:
            if it["accessible"] and it["chemin"]:
                lignes.append((f"Duree : {it['duree']:.1f} min ({it['nb_arcs']} arcs)", COUL_CHEMIN))
                # somme des poids du chemin, pour voir d'ou vient la duree
                somme = " + ".join(texte_poids(self.g.poids_arc(u, v)) for u, v in zip(it["chemin"], it["chemin"][1:]))
                somme = f"= {somme}"
                for k in range(0, len(somme), 38):
                    lignes.append((somme[k:k + 38], COUL_CHEMIN))
                if self.duree_ref not in (None, math.inf) and self.i_scenario:
                    retard = it["duree"] - self.duree_ref
                    rel = f" ({retard / self.duree_ref:+.0%})" if self.duree_ref > 0 else ""
                    lignes.append((f"Reference : {self.duree_ref:.1f} min", COUL_GRIS))
                    lignes.append((f"Retard : {retard:+.1f} min{rel}", COUL_FERME if retard > 0 else COUL_GRIS))
                chemin = " > ".join(it["chemin"])
                for k in range(0, len(chemin), 38):
                    lignes.append((chemin[k:k + 38], COUL_GRIS))
                if it["fermetures"]:
                    lignes.append((f"travaux : {len(it['fermetures'])} troncon(s)", COUL_MODIFIE))
            else:
                lignes.append(("INACCESSIBLE", COUL_FERME))
        if self.mode == "accessibilite":
            n_rouge = sum(1 for c in self.couleurs_sommets().values() if c == COUL_FERME)
            lignes.append((f"Non atteignables : {n_rouge}", COUL_FERME if n_rouge else COUL_GRIS))
            lignes.append(("couleur = caserne d'origine (BFS)", COUL_GRIS))
        if self.mode == "cfc":
            n = len(set(self.couleurs_sommets().values()))
            lignes.append((f"CFC (couleurs) : {n}", COUL_TEXTE))
        if self.mode == "itineraires":
            lignes.append(("cercles jaunes = demandes", COUL_GRIS))
            lignes.append(("couleur = caserne retenue", COUL_GRIS))
        if self.afficher_poids and self.poids_caches:
            lignes.append((f"{self.poids_caches} poids caches : zoomer", COUL_GRIS))
        if self.message:
            lignes.append((self.message, COUL_MODIFIE))
        if self.aide:
            lignes += [
                ("", None),
                ("--- commandes (H) ---", COUL_GRIS),
                ("clic gauche : source", COUL_GRIS),
                ("clic droit  : cible", COUL_GRIS),
                ("1 / 2 / 3   : Dijkstra / BF / FW", COUL_GRIS),
                ("S           : scenario suivant", COUL_GRIS),
                ("W           : afficher les poids", COUL_GRIS),
                ("M           : mode suivant", COUL_GRIS),
                ("Espace      : animer l'exploration", COUL_GRIS),
                ("molette     : zoom", COUL_GRIS),
                ("clic milieu : deplacer la vue", COUL_GRIS),
                ("R : reinitialiser   P : capture", COUL_GRIS),
                ("Echap       : quitter", COUL_GRIS),
                ("", None),
                ("rouge pointille = route fermee", COUL_FERME),
                ("orange = temps modifie", COUL_MODIFIE),
            ]
        return lignes

    def dessiner_panneau(self, surf):
        x0 = self.largeur - PANNEAU
        pygame.draw.rect(surf, (28, 31, 42), (x0, 0, PANNEAU, self.hauteur))
        police = pygame.font.SysFont("consolas", 15)
        y = 14
        for texte, couleur in self.lignes_panneau():
            if texte:
                surf.blit(police.render(texte, True, couleur), (x0 + 14, y))
            y += 20

    # ------------------------------------------------------------ boucle

    def gerer_evenement(self, ev):
        if ev.type == pygame.QUIT:
            return False
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                return False
            if ev.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.algo = ALGOS[ev.key - pygame.K_1]
                self.recalculer()
            elif ev.key == pygame.K_s:
                self.changer_scenario(self.i_scenario + 1)
            elif ev.key == pygame.K_m:
                self.changer_mode(MODES[(MODES.index(self.mode) + 1) % len(MODES)])
            elif ev.key == pygame.K_SPACE and self.exploration:
                self.t_exploration = 0.0
            elif ev.key == pygame.K_w:
                self.afficher_poids = not self.afficher_poids
                self.invalider()
            elif ev.key == pygame.K_h:
                self.aide = not self.aide
            elif ev.key == pygame.K_r:
                self.zoom, self.pan = 1.0, Vector2(0, 0)
                self.source = self.cible = None
                self.recalculer()
            elif ev.key == pygame.K_p:
                (RACINE / "resultats").mkdir(exist_ok=True)
                pygame.image.save(pygame.display.get_surface(), str(RACINE / "resultats" / "capture_visu.png"))
                self.message = "capture : resultats/capture_visu.png"
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.pos[0] < self.largeur - PANNEAU:
            if ev.button in (1, 3):
                s = self.sommet_sous(ev.pos)
                if s is not None:
                    if ev.button == 1:
                        self.source = s
                    else:
                        self.cible = s
                    self.recalculer()
        elif ev.type == pygame.MOUSEWHEEL:
            self.zoomer(1.15 if ev.y > 0 else 1 / 1.15, pygame.mouse.get_pos())
        elif ev.type == pygame.MOUSEMOTION:
            if ev.buttons[1]:
                self.pan += Vector2(ev.rel)
                self.invalider()
            self.survol = self.sommet_sous(ev.pos) if ev.pos[0] < self.largeur - PANNEAU else None
        return True

    def lancer(self):
        ecran = pygame.display.set_mode((self.largeur, self.hauteur))
        pygame.display.set_caption("Novapolis - visualisation du reseau routier")
        horloge = pygame.time.Clock()
        actif = True
        while actif:
            dt = horloge.tick(60) / 1000.0
            for ev in pygame.event.get():
                actif = self.gerer_evenement(ev) and actif
            self.dessiner(ecran, dt)
            pygame.display.flip()
        pygame.quit()


def capturer(vis, fichier):
    # rendu d'une seule image sans fenetre (tests, rapport)
    surf = pygame.Surface((vis.largeur, vis.hauteur))
    vis.t_vehicule = 1e9  # vehicule arrive au bout
    vis.dessiner(surf, 0.0)
    Path(fichier).parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(fichier))
    return surf


def main(arguments=None):
    parser = argparse.ArgumentParser(description="Visualisation pygame du reseau routier de Novapolis")
    parser.add_argument("--donnees", type=Path, default=RACINE / "data" / "petit")
    parser.add_argument("--source", default=None)
    parser.add_argument("--cible", default=None)
    parser.add_argument("--scenario", default=None)
    parser.add_argument("--algo", choices=ALGOS, default="dijkstra")
    parser.add_argument("--mode", choices=MODES, default="chemin")
    parser.add_argument("--poids", action="store_true", help="affiche le poids (duree) de chaque arc")
    parser.add_argument("--capture", type=Path, default=None, help="enregistre une image PNG sans ouvrir de fenetre")
    args = parser.parse_args(arguments)

    if args.capture:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()

    # chemin relatif introuvable depuis le dossier courant : on le cherche depuis la racine du projet
    if not args.donnees.exists() and (RACINE / args.donnees).exists():
        args.donnees = RACINE / args.donnees
    if not args.donnees.exists():
        print(f"[ERREUR] dossier de donnees introuvable : {args.donnees}")
        return 1

    autoriser_neg = "negatif" in str(args.donnees)
    vis = Visualiseur(charger_jeu_donnees(args.donnees, autoriser_temps_negatifs=autoriser_neg))
    vis.algo = args.algo
    vis.mode = args.mode
    vis.afficher_poids = args.poids
    for s in (args.source, args.cible):
        if s is not None and s not in vis.pos_monde:
            print(f"[ERREUR] site inconnu : {s}")
            return 1
    vis.source, vis.cible = args.source, args.cible
    if args.scenario:
        if args.scenario not in vis.scenarios:
            print(f"[ERREUR] scenario inconnu : {args.scenario}. Disponibles : {vis.scenarios[1:]}")
            return 1
        vis.changer_scenario(vis.scenarios.index(args.scenario))
    else:
        vis.recalculer()

    if args.capture:
        capturer(vis, args.capture)
        print(f"[OK] image enregistree : {args.capture}")
        pygame.quit()
        return 0

    vis.lancer()
    return 0


if __name__ == "__main__":
    sys.exit(main())
