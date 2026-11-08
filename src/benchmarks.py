import csv
import gc
import math
import random
import statistics
import time
from collections import deque
from pathlib import Path

import matplotlib

# pas de fenetre : les graphiques sont seulement ecrits dans des fichiers
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from src.arbres import kruskal, prim, trouver_composantes
from src.chemins import bellman_ford, dijkstra, floyd_warshall
from src.graphe import Graphe
from src.parcours import bfs, dfs

TAILLES = [100, 500, 1000, 2000, 5000]
# nombre d'aretes par sommet : un graphe vraiment dense a 5000 sommets aurait 12,5 millions d'aretes
DENSITES = {"creux": 3, "dense": 20}
REPETITIONS = 5
# passes non chronometrees : les premieres passes sur un graphe sont lentes (cache encore froid)
ECHAUFFEMENT = 3

# floyd-warshall en O(n^3) seulement sur de petits graphes : n^3 = 10^9 operations pour n = 1000
# tailles qui doublent : en O(n^3), chaque doublement doit multiplier le temps par 8
TAILLES_FLOYD = [25, 50, 100, 200, 400]


def _depuis_le_premier_sommet(algorithme):
    # les parcours et plus courts chemins de B partent d'une source : on prend toujours la meme
    return lambda g: algorithme(g, g.sommets()[0])


# memes graphes pour tous ces algos : arbres couvrants (C), parcours et plus courts chemins (B)
ALGORITHMES = {
    "kruskal": kruskal,
    "prim": prim,
    "bfs": _depuis_le_premier_sommet(bfs),
    "dfs": _depuis_le_premier_sommet(dfs),
    "dijkstra": _depuis_le_premier_sommet(dijkstra),
    "bellman_ford": _depuis_le_premier_sommet(bellman_ford),
}
ALGORITHMES_FLOYD = {"floyd_warshall": floyd_warshall}

# complexites du sujet, en nombre d'operations pour n sommets et m aretes
# graphe non oriente : les parcours et plus courts chemins lisent chaque arete dans les 2 sens, soit 2m arcs
COMPLEXITES = {
    "kruskal": lambda n, m: m * math.log2(m),
    "prim": lambda n, m: m * math.log2(n),
    "bfs": lambda n, m: n + 2 * m,
    "dfs": lambda n, m: n + 2 * m,
    "dijkstra": lambda n, m: (n + 2 * m) * math.log2(n),
    "bellman_ford": lambda n, m: n * 2 * m,
    "floyd_warshall": lambda n, m: n ** 3,
}

# chaque algo garde son style d'un graphique a l'autre, couleurs dans l'ordre fixe de la palette
STYLES = {
    "kruskal": {"nom": "Kruskal", "couleur": "#2a78d6", "marqueur": "o"},
    "prim": {"nom": "Prim", "couleur": "#eb6834", "marqueur": "s"},
    "bfs": {"nom": "BFS", "couleur": "#1baf7a", "marqueur": "^"},
    "dfs": {"nom": "DFS", "couleur": "#eda100", "marqueur": "v"},
    "dijkstra": {"nom": "Dijkstra", "couleur": "#e87ba4", "marqueur": "D"},
    "bellman_ford": {"nom": "Bellman-Ford", "couleur": "#008300", "marqueur": "P"},
    "floyd_warshall": {"nom": "Floyd-Warshall", "couleur": "#6250d6", "marqueur": "X"},
}

STYLE_GRAPHIQUE = {
    "figure.facecolor": "#fcfcfb",
    "axes.facecolor": "#fcfcfb",
    "savefig.facecolor": "#fcfcfb",
    "axes.edgecolor": "#c3c2b7",
    "axes.labelcolor": "#52514e",
    "axes.titlecolor": "#0b0b0b",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#e1e0d9",
    "grid.linewidth": 0.8,
    "xtick.color": "#898781",
    "ytick.color": "#898781",
    "xtick.labelcolor": "#52514e",
    "ytick.labelcolor": "#52514e",
    "text.color": "#0b0b0b",
    "legend.frameon": False,
}


def generer_graphe_mesure(n, m, graine):
    # en memoire : generer_jeu_donnees ecrit des csv et ne permet pas de choisir m pour la fibre
    m_max = n * (n - 1) // 2
    if m < n - 1 or m > m_max:
        raise ValueError(f"Il faut entre {n - 1} et {m_max} aretes pour {n} sommets (recu : {m}).")

    rng = random.Random(graine)
    pad = len(str(n))
    sommets = [f"S{str(i).zfill(pad)}" for i in range(n)]

    g = Graphe(oriente=False)
    for s in sommets:
        g.ajouter_sommet(s)

    vues = set()

    def ajouter(u, v):
        cle = (u, v) if u < v else (v, u)
        if u == v or cle in vues:
            return False
        vues.add(cle)
        g.ajouter_arc(u, v, float(rng.randint(1, 1000)))
        return True

    # arbre aleatoire d'abord : tous les graphes mesures sont connexes
    ordre = sommets[:]
    rng.shuffle(ordre)
    for i in range(1, n):
        ajouter(ordre[i], ordre[rng.randrange(i)])

    while len(vues) < m:
        ajouter(rng.choice(sommets), rng.choice(sommets))

    return g


def mesurer(fonction, graphe, repetitions=REPETITIONS, horloge=time.perf_counter, echauffement=ECHAUFFEMENT):
    if repetitions < REPETITIONS:
        raise ValueError(f"Il faut au moins {REPETITIONS} repetitions (recu : {repetitions}).")

    temps = []
    # sans ramasse-miettes pendant la mesure : il ajouterait du bruit
    gc_actif = gc.isenabled()
    gc.collect()
    gc.disable()
    try:
        for _ in range(echauffement):
            fonction(graphe)
        for _ in range(repetitions):
            debut = horloge()
            fonction(graphe)
            temps.append(horloge() - debut)
    finally:
        if gc_actif:
            gc.enable()

    return {
        "moyenne_s": statistics.mean(temps),
        "mediane_s": statistics.median(temps),
        "ecart_type_s": statistics.stdev(temps),
    }


def _mesurer_plan(lignes, nom_densite, aretes_par_sommet, tailles, algorithmes, repetitions, graine):
    for n in tailles:
        m = aretes_par_sommet * n
        # une graine par graphe, ecrite dans le csv pour pouvoir le regenerer
        graine_graphe = graine + 100 * n + aretes_par_sommet
        g = generer_graphe_mesure(n, m, graine_graphe)

        # meme graphe pour tous les algos, generation hors de la mesure
        for nom_algo, fonction in algorithmes.items():
            resultat = mesurer(fonction, g, repetitions)
            lignes.append({
                "algorithme": nom_algo,
                "densite": nom_densite,
                "n": n,
                "m": m,
                "graine": graine_graphe,
                "repetitions": repetitions,
                "moyenne_s": resultat["moyenne_s"],
                "mediane_s": resultat["mediane_s"],
                "ecart_type_s": resultat["ecart_type_s"],
            })


def lancer_benchmarks(tailles=TAILLES, densites=DENSITES, repetitions=REPETITIONS, graine=42,
                      algorithmes=ALGORITHMES, dossier_resultats="resultats", tailles_floyd=TAILLES_FLOYD):
    lignes = []

    for nom_densite, aretes_par_sommet in densites.items():
        _mesurer_plan(lignes, nom_densite, aretes_par_sommet, tailles, algorithmes, repetitions, graine)

    # floyd-warshall a part, sur des graphes creux plus petits
    if tailles_floyd:
        _mesurer_plan(lignes, "floyd", DENSITES["creux"], tailles_floyd, ALGORITHMES_FLOYD, repetitions, graine)

    dossier = Path(dossier_resultats)
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = dossier / "benchmarks.csv"
    with open(fichier, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        writer.writeheader()
        writer.writerows(lignes)

    return {"lignes": lignes, "fichier_csv": str(fichier)}


def formater_benchmarks(lignes):
    texte = [f"{'Algorithme':<16} | {'Densite':<7} | {'n':>5} | {'m':>6} | {'Moyenne (ms)':>12} | {'Ecart-type (ms)':>15}"]
    texte.append("-" * 78)
    for l in lignes:
        texte.append(
            f"{l['algorithme']:<16} | {l['densite']:<7} | {l['n']:>5} | {l['m']:>6} | "
            f"{l['moyenne_s'] * 1000:>12.3f} | {l['ecart_type_s'] * 1000:>15.3f}"
        )
    return "\n".join(texte)


def temps_par_operation_ns(ligne):
    # presque constant quand n augmente = la mesure suit la complexite theorique
    operations = COMPLEXITES[ligne["algorithme"]](ligne["n"], ligne["m"])
    return ligne["moyenne_s"] * 1e9 / operations


def _series(lignes, densite):
    series = {}
    for l in lignes:
        if l["densite"] == densite:
            series.setdefault(l["algorithme"], []).append(l)
    return series


def _axe_des_tailles(ax, tailles):
    # plage elargie a droite pour laisser la place aux noms des courbes
    ax.set_xscale("log")
    ax.set_xlim(min(tailles) * 0.8, max(tailles) * 4)
    ax.set_xticks(tailles)
    ax.set_xticks([], minor=True)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x)}"))
    ax.set_xlabel("Nombre de sommets n (échelle log)")


def _nommer_les_courbes(ax, fins, ecart_pt=11):
    # nom au bout de chaque courbe, decale si deux fins de courbes sont trop proches
    ax.figure.canvas.draw()
    pt_par_px = 72 / ax.figure.dpi
    hauteur_precedente = None
    for nom, x, y in sorted(fins, key=lambda f: f[2]):
        hauteur = ax.transData.transform((x, y))[1] * pt_par_px
        decalage = 0
        if hauteur_precedente is not None and hauteur < hauteur_precedente + ecart_pt:
            decalage = hauteur_precedente + ecart_pt - hauteur
        hauteur_precedente = hauteur + decalage
        ax.annotate(nom, (x, y), xytext=(9, decalage), textcoords="offset points",
                    va="center", fontsize=9, color="#52514e")


def _tracer_courbes(ax, series, valeurs, erreurs=None):
    fins = []
    for algo, points in series.items():
        style = STYLES[algo]
        x = [p["n"] for p in points]
        y = [valeurs(p) for p in points]
        # barres tracees a part pour qu'elles n'apparaissent pas dans la legende
        if erreurs:
            ax.errorbar(x, y, yerr=[erreurs(p) for p in points], fmt="none",
                        ecolor=style["couleur"], elinewidth=1, capsize=0)
        # le marqueur double la couleur : la courbe reste lisible sans les couleurs
        ax.plot(x, y, color=style["couleur"], marker=style["marqueur"], markersize=6,
                markeredgecolor="#fcfcfb", markeredgewidth=1, linewidth=1.8, label=style["nom"])
        fins.append((style["nom"], x[-1], y[-1]))
    return fins


def _tracer_temps(lignes, densite, titre, fichier):
    series = _series(lignes, densite)
    fig, ax = plt.subplots(figsize=(7.5, 4.8), dpi=200)

    fins = _tracer_courbes(ax, series,
                           lambda p: p["moyenne_s"] * 1000,
                           lambda p: p["ecart_type_s"] * 1000)

    _axe_des_tailles(ax, sorted({l["n"] for l in lignes}))
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:g}"))
    ax.set_ylabel("Temps moyen (ms, échelle log)")
    ax.set_title(titre, loc="left", fontsize=12)
    ax.legend(loc="upper left", fontsize=9)
    _nommer_les_courbes(ax, fins)
    repetitions = lignes[0]["repetitions"]
    fig.text(0.01, 0.01, f"Moyenne de {repetitions} répétitions après échauffement, barres : écart-type. Mêmes graphes pour tous les algorithmes.",
             fontsize=8, color="#52514e")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(fichier)
    plt.close(fig)


def _tracer_temps_sur_theorie(lignes, fichier):
    densites = list(dict.fromkeys(l["densite"] for l in lignes))
    fig, axes = plt.subplots(1, len(densites), figsize=(5 * len(densites), 5.2), dpi=200, sharey=True, squeeze=False)

    fins_par_axe = []
    for ax, densite in zip(axes[0], densites):
        series = _series(lignes, densite)
        fins_par_axe.append(_tracer_courbes(ax, series, temps_par_operation_ns))
        # chaque panneau garde ses propres tailles, sinon les graduations se chevauchent
        _axe_des_tailles(ax, sorted({l["n"] for l in lignes if l["densite"] == densite}))
        ax.set_title(f"Graphes {_titre_densite(densite)} (m = {_aretes_par_sommet(series)}n)",
                     loc="left", fontsize=11)

    # echelle log : bellman-ford s'arrete bien avant son pire cas, il est des centaines de fois sous la theorie
    axes[0][0].set_yscale("log")
    axes[0][0].yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:g}"))
    for ax, fins in zip(axes[0], fins_par_axe):
        _nommer_les_courbes(ax, fins)

    axes[0][0].set_ylabel("Temps par opération théorique (ns, échelle log)")
    # legende commune : chaque algo une seule fois, meme s'il n'est que dans un panneau
    legende = {}
    for ax in axes[0]:
        for poignee, nom in zip(*ax.get_legend_handles_labels()):
            legende.setdefault(nom, poignee)
    fig.legend(list(legende.values()), list(legende.keys()), loc="upper right", ncol=min(4, len(legende)), fontsize=9)
    fig.suptitle("Temps mesuré divisé par la complexité théorique", x=0.01, ha="left", fontsize=12)
    fig.text(0.01, 0.01, "Courbe plate = théorie confirmée. Arêtes lues dans les 2 sens pour BFS, DFS, Dijkstra et "
             "Bellman-Ford (2m arcs). Bellman-Ford : pire cas n·2m, arrêt anticipé en pratique.",
             fontsize=8, color="#52514e")
    fig.tight_layout(rect=(0, 0.05, 1, 0.86))
    fig.savefig(fichier)
    plt.close(fig)


def _aretes_par_sommet(series):
    premier = next(iter(series.values()))[0]
    return premier["m"] // premier["n"]


def _titre_densite(densite):
    return {"dense": "denses", "floyd": "creux, petites tailles"}.get(densite, densite)


def tracer_graphiques(lignes, dossier_resultats="resultats"):
    dossier = Path(dossier_resultats)
    dossier.mkdir(parents=True, exist_ok=True)
    fichiers = []

    with plt.rc_context(STYLE_GRAPHIQUE):
        for densite in dict.fromkeys(l["densite"] for l in lignes):
            ratio = _aretes_par_sommet(_series(lignes, densite))
            fichier = dossier / f"temps_{densite}.png"
            _tracer_temps(lignes=[l for l in lignes if l["densite"] == densite], densite=densite,
                          titre=f"Temps d'exécution selon la taille, graphes {_titre_densite(densite)} (m = {ratio}n)",
                          fichier=fichier)
            fichiers.append(str(fichier))

        fichier = dossier / "temps_sur_theorie.png"
        _tracer_temps_sur_theorie(lignes, fichier)
        fichiers.append(str(fichier))

    return fichiers


def reconstruire_en_ordre_bfs(graphe):
    # memes sommets et memes aretes, alloues dans l'ordre ou le BFS les lira
    ordre = []
    vus = set()
    for depart in graphe.sommets():
        if depart in vus:
            continue
        vus.add(depart)
        file = deque([depart])
        while file:
            u = file.popleft()
            ordre.append(u)
            for v, _ in graphe.successeurs(u):
                if v not in vus:
                    vus.add(v)
                    file.append(v)

    h = Graphe(oriente=graphe.oriente)
    for u in ordre:
        h._sommets[u] = dict(graphe._sommets[u])
        h._adj[u] = [
            # + 0.0 cree un nouveau flottant, sinon l'ancien objet reste utilise
            {"cible": a["cible"], "poids": a["poids"] + 0.0, "attributs": dict(a["attributs"])}
            for a in graphe._adj[u]
        ]
    return h


def lire_adjacence(graphe):
    # lecture seule de la memoire du graphe : ni ensemble, ni file, ni tri
    total = 0
    for u in graphe._adj:
        for arc in graphe._adj[u]:
            if arc["cible"]:
                total += 1
    return total


DISPOSITIONS = {
    "originale": lambda g: g,
    "copie": lambda g: g.copie(),
    "ordre_bfs": reconstruire_en_ordre_bfs,
}

STYLES_DISPOSITIONS = {
    "originale": {"nom": "Originale", "couleur": "#2a78d6", "marqueur": "o"},
    "copie": {"nom": "Copie", "couleur": "#eb6834", "marqueur": "s"},
    "ordre_bfs": {"nom": "Ordre du BFS", "couleur": "#1baf7a", "marqueur": "^"},
}


def experience_localite(tailles=(100, 500, 1000, 2000, 5000, 10000), aretes_par_sommet=20, graines=3,
                        repetitions=REPETITIONS, graine=42, dossier_resultats="resultats"):
    # meme graphe et meme algorithme : seule la disposition en memoire change
    mesures = []
    for n in tailles:
        m = aretes_par_sommet * n
        for i in range(graines):
            g = generer_graphe_mesure(n, m, graine + i)
            for nom, disposer in DISPOSITIONS.items():
                h = disposer(g)
                mesures.append({
                    "n": n,
                    "disposition": nom,
                    # mediane : un seul pic du systeme ne doit pas decider du resultat
                    "bfs": mesurer(trouver_composantes, h, repetitions)["mediane_s"] * 1e9 / (n + m),
                    "lecture": mesurer(lire_adjacence, h, repetitions)["mediane_s"] * 1e9 / (2 * m),
                })

    lignes = []
    for n in tailles:
        m = aretes_par_sommet * n
        for nom in DISPOSITIONS:
            valeurs = [x for x in mesures if x["n"] == n and x["disposition"] == nom]
            lignes.append({
                "n": n,
                "m": m,
                "disposition": nom,
                "graines": f"{graine}-{graine + graines - 1}",
                "repetitions": repetitions,
                "bfs_ns_par_operation": statistics.mean(x["bfs"] for x in valeurs),
                "lecture_ns_par_arc": statistics.mean(x["lecture"] for x in valeurs),
            })

    dossier = Path(dossier_resultats)
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = dossier / "localite.csv"
    with open(fichier, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        writer.writeheader()
        writer.writerows(lignes)

    return {"lignes": lignes, "fichier_csv": str(fichier)}


def formater_localite(lignes):
    texte = [f"{'n':>6} | {'m':>7} | {'Disposition':<11} | {'BFS (ns/op)':>11} | {'Lecture (ns/arc)':>16}"]
    texte.append("-" * 63)
    for l in lignes:
        texte.append(
            f"{l['n']:>6} | {l['m']:>7} | {l['disposition']:<11} | "
            f"{l['bfs_ns_par_operation']:>11.1f} | {l['lecture_ns_par_arc']:>16.1f}"
        )
    return "\n".join(texte)


def tracer_localite(lignes, dossier_resultats="resultats"):
    dossier = Path(dossier_resultats)
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = dossier / "temps_localite.png"
    tailles = sorted({l["n"] for l in lignes})
    panneaux = [
        ("bfs_ns_par_operation", "BFS complet"),
        ("lecture_ns_par_arc", "Lecture seule des arcs"),
    ]

    with plt.rc_context(STYLE_GRAPHIQUE):
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), dpi=200, sharey=True)
        fins_par_axe = []
        for ax, (colonne, titre) in zip(axes, panneaux):
            fins = []
            for nom, style in STYLES_DISPOSITIONS.items():
                points = [l for l in lignes if l["disposition"] == nom]
                x = [p["n"] for p in points]
                y = [p[colonne] for p in points]
                ax.plot(x, y, color=style["couleur"], marker=style["marqueur"], markersize=6,
                        markeredgecolor="#fcfcfb", markeredgewidth=1, linewidth=1.8, label=style["nom"])
                fins.append((style["nom"], x[-1], y[-1]))
            fins_par_axe.append(fins)
            _axe_des_tailles(ax, tailles)
            ax.set_title(titre, loc="left", fontsize=11)

        axes[0].set_ylim(bottom=0)
        for ax, fins in zip(axes, fins_par_axe):
            _nommer_les_courbes(ax, fins)

        axes[0].set_ylabel("Temps par opération (ns)")
        poignees, noms = axes[0].get_legend_handles_labels()
        fig.legend(poignees, noms, loc="upper right", ncol=len(noms), fontsize=9)
        ratio = lignes[0]["m"] // lignes[0]["n"]
        fig.suptitle(f"Même graphe, disposition en mémoire différente (m = {ratio}n)", x=0.01, ha="left", fontsize=12)
        fig.text(0.01, 0.01, f"Médiane de {lignes[0]['repetitions']} répétitions après échauffement, moyennée sur les graines {lignes[0]['graines']}.",
                 fontsize=8, color="#52514e")
        fig.tight_layout(rect=(0, 0.03, 1, 0.97))
        fig.savefig(fichier)
        plt.close(fig)

    return str(fichier)
