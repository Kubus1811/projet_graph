import csv

import matplotlib.pyplot as plt
import pytest
from src.arbres import trouver_composantes
from src.benchmarks import (
    ALGORITHMES,
    ALGORITHMES_FLOYD,
    COMPLEXITES,
    DISPOSITIONS,
    ECHAUFFEMENT,
    STYLES,
    experience_localite,
    formater_benchmarks,
    formater_localite,
    generer_graphe_mesure,
    lancer_benchmarks,
    lire_adjacence,
    mesurer,
    reconstruire_en_ordre_bfs,
    temps_par_operation_ns,
    tracer_graphiques,
    tracer_localite,
)

PETITES_DENSITES = {"creux": 2, "dense": 4}


def test_graphe_mesure_a_la_taille_demandee():
    g = generer_graphe_mesure(50, 150, graine=1)

    assert g.oriente is False
    assert g.nombre_sommets() == 50
    assert g.nombre_arcs() == 150


def test_graphe_mesure_est_connexe():
    # le minimum d'aretes : un seul arbre, sinon la generation est fausse
    assert len(trouver_composantes(generer_graphe_mesure(200, 199, graine=1))) == 1


def test_graphe_mesure_complet():
    assert generer_graphe_mesure(5, 10, graine=1).nombre_arcs() == 10


def test_graphe_mesure_sans_boucle_et_poids_positifs():
    g = generer_graphe_mesure(30, 100, graine=1)

    for u, v, poids in g.arcs():
        assert u != v
        assert poids > 0


def test_graphe_mesure_meme_graine_meme_graphe():
    assert generer_graphe_mesure(50, 150, graine=7).arcs() == generer_graphe_mesure(50, 150, graine=7).arcs()


def test_graphe_mesure_autre_graine_autre_graphe():
    assert generer_graphe_mesure(50, 150, graine=7).arcs() != generer_graphe_mesure(50, 150, graine=8).arcs()


@pytest.mark.parametrize("n,m", [(10, 8), (5, 11)])
def test_graphe_mesure_refuse_un_nombre_d_aretes_impossible(n, m):
    with pytest.raises(ValueError):
        generer_graphe_mesure(n, m, graine=1)


def test_mesurer_calcule_moyenne_et_ecart_type():
    # horloge factice : durees de 1, 2, 3, 4 et 5 secondes
    instants = iter([0, 1, 10, 12, 20, 23, 30, 34, 40, 45])

    res = mesurer(lambda g: None, None, repetitions=5, horloge=lambda: next(instants))

    assert res["moyenne_s"] == 3
    assert res["mediane_s"] == 3
    assert res["ecart_type_s"] == pytest.approx(1.5811388)


def test_mesurer_mediane_resiste_a_un_pic():
    # durees de 1, 1, 1, 1 et 100 secondes
    instants = iter([0, 1, 10, 11, 20, 21, 30, 31, 40, 140])

    res = mesurer(lambda g: None, None, repetitions=5, horloge=lambda: next(instants))

    assert res["mediane_s"] == 1
    assert res["moyenne_s"] == pytest.approx(20.8)


def test_mesurer_appelle_l_algo_a_chaque_repetition():
    appels = []

    mesurer(appels.append, "graphe", repetitions=7)

    assert appels == ["graphe"] * (7 + ECHAUFFEMENT)


def test_mesurer_ne_chronometre_pas_l_echauffement():
    appels_horloge = []
    appels_algo = []

    def horloge():
        # a chaque lecture : combien de passes de l'algo ont deja eu lieu
        appels_horloge.append(len(appels_algo))
        return 0.0

    mesurer(appels_algo.append, "graphe", repetitions=5, horloge=horloge, echauffement=3)

    # premiere lecture apres les 3 passes d'echauffement, 2 lectures par repetition
    assert appels_horloge[0] == 3
    assert len(appels_horloge) == 10


def test_mesurer_refuse_moins_de_cinq_repetitions():
    with pytest.raises(ValueError):
        mesurer(lambda g: None, None, repetitions=4)


def test_campagne_tous_les_algos_sur_les_memes_graphes(tmp_path):
    vus = {"a": [], "b": []}
    algorithmes = {nom: (lambda g, nom=nom: vus[nom].append(g.arcs())) for nom in vus}

    lancer_benchmarks(tailles=[10, 20], densites=PETITES_DENSITES, algorithmes=algorithmes,
                      dossier_resultats=tmp_path, tailles_floyd=())

    assert vus["a"] == vus["b"]
    # 2 tailles x 2 densites x (5 repetitions + echauffement)
    assert len(vus["a"]) == 4 * (5 + ECHAUFFEMENT)


def test_campagne_ecrit_le_csv(tmp_path):
    res = lancer_benchmarks(tailles=[10, 20], densites=PETITES_DENSITES, dossier_resultats=tmp_path,
                            tailles_floyd=(10, 20))

    with open(res["fichier_csv"], encoding="utf-8") as f:
        lignes = list(csv.DictReader(f))

    # 6 algos x 2 tailles x 2 densites, plus floyd-warshall sur 2 tailles
    assert len(lignes) == 6 * 2 * 2 + 2
    assert {l["algorithme"] for l in lignes} == {"kruskal", "prim", "bfs", "dfs", "dijkstra", "bellman_ford", "floyd_warshall"}
    assert {l["densite"] for l in lignes if l["algorithme"] == "floyd_warshall"} == {"floyd"}
    assert all(float(l["moyenne_s"]) > 0 for l in lignes)
    assert all(l["repetitions"] == "5" for l in lignes)


def test_campagne_m_et_graine_notes(tmp_path):
    lignes = lancer_benchmarks(tailles=[10], densites={"creux": 3}, graine=42, dossier_resultats=tmp_path,
                               tailles_floyd=())["lignes"]

    assert lignes[0]["n"] == 10
    assert lignes[0]["m"] == 30
    assert lignes[0]["graine"] == 42 + 100 * 10 + 3


def test_campagne_graine_regenere_le_graphe_mesure(tmp_path):
    arcs = []
    lignes = lancer_benchmarks(tailles=[20], densites={"creux": 3}, dossier_resultats=tmp_path,
                               algorithmes={"a": lambda g: arcs.append(g.arcs())}, tailles_floyd=())["lignes"]

    assert generer_graphe_mesure(20, 60, lignes[0]["graine"]).arcs() == arcs[0]


def test_sortie_lisible_en_millisecondes():
    texte = formater_benchmarks([{
        "algorithme": "kruskal",
        "densite": "creux",
        "n": 100,
        "m": 300,
        "moyenne_s": 0.0015,
        "ecart_type_s": 0.0001,
    }])

    assert "kruskal" in texte
    assert "1.500" in texte
    assert "0.100" in texte


def test_chaque_algo_mesure_a_sa_complexite_et_son_style():
    tous = set(ALGORITHMES) | set(ALGORITHMES_FLOYD)

    assert tous == set(COMPLEXITES) == set(STYLES)


@pytest.mark.parametrize("algo,attendu", [
    ("kruskal", 64 * 6),
    ("prim", 64 * 4),
    ("bfs", 16 + 128),
    ("dfs", 16 + 128),
    ("dijkstra", (16 + 128) * 4),
    ("bellman_ford", 16 * 128),
    ("floyd_warshall", 16 ** 3),
])
def test_complexites_theoriques(algo, attendu):
    assert COMPLEXITES[algo](16, 64) == attendu


def test_temps_par_operation_en_nanosecondes():
    ligne = {"algorithme": "bfs", "n": 100, "m": 450, "moyenne_s": 0.001}

    # 1 ms pour 1000 operations : 1000 ns par operation
    assert temps_par_operation_ns(ligne) == pytest.approx(1000)


def test_graphiques_ecrits_sans_figure_ouverte(tmp_path):
    lignes = lancer_benchmarks(tailles=[10, 20, 40], densites=PETITES_DENSITES, dossier_resultats=tmp_path,
                               tailles_floyd=(10, 20, 40))["lignes"]

    fichiers = tracer_graphiques(lignes, dossier_resultats=tmp_path / "images")

    assert sorted(p.name for p in (tmp_path / "images").iterdir()) == [
        "temps_creux.png",
        "temps_dense.png",
        "temps_floyd.png",
        "temps_sur_theorie.png",
    ]
    assert len(fichiers) == 4
    assert all((tmp_path / "images" / p).stat().st_size > 0 for p in ["temps_creux.png", "temps_dense.png"])
    assert plt.get_fignums() == []


def aretes_normalisees(g):
    return sorted((min(u, v), max(u, v), p) for u, v, p in g.arcs())


@pytest.mark.parametrize("nom", list(DISPOSITIONS))
def test_chaque_disposition_garde_le_meme_graphe(nom):
    g = generer_graphe_mesure(60, 300, graine=3)
    avant = g.arcs()

    h = DISPOSITIONS[nom](g)

    # sinon l'experience comparerait deux graphes differents
    assert sorted(h.sommets()) == sorted(g.sommets())
    assert aretes_normalisees(h) == aretes_normalisees(g)
    assert trouver_composantes(h) == trouver_composantes(g)
    assert g.arcs() == avant


def test_ordre_bfs_alloue_de_nouveaux_objets():
    g = generer_graphe_mesure(20, 40, graine=3)

    h = reconstruire_en_ordre_bfs(g)

    u = g.sommets()[0]
    assert h._adj[u] is not g._adj[u]
    assert h._adj[u][0] is not g._adj[u][0]
    assert h._adj[u][0]["poids"] is not g._adj[u][0]["poids"]


def test_ordre_bfs_garde_les_sommets_isoles_et_le_sens():
    g = graphe_avec_sommet_isole()

    h = reconstruire_en_ordre_bfs(g)

    assert h.oriente is False
    assert sorted(h.sommets()) == ["A", "B", "Z"]
    assert h.attributs_sommet("Z") == {"type": "quartier"}


def graphe_avec_sommet_isole():
    g = generer_graphe_mesure(2, 1, graine=1).__class__(oriente=False)
    g.ajouter_arc("A", "B", 1.0)
    g.ajouter_sommet("Z", type="quartier")
    return g


def test_lire_adjacence_compte_chaque_arc():
    # en non oriente chaque arete existe dans les deux sens
    assert lire_adjacence(generer_graphe_mesure(30, 90, graine=1)) == 180


def test_experience_localite_ecrit_le_csv_et_le_graphique(tmp_path):
    res = experience_localite(tailles=(20, 40), aretes_par_sommet=3, graines=2, dossier_resultats=tmp_path)

    with open(res["fichier_csv"], encoding="utf-8") as f:
        lignes = list(csv.DictReader(f))

    # 2 tailles x 3 dispositions
    assert len(lignes) == 6
    assert {l["disposition"] for l in lignes} == set(DISPOSITIONS)
    assert all(float(l["bfs_ns_par_operation"]) > 0 for l in lignes)
    assert all(l["graines"] == "42-43" for l in lignes)

    fichier = tracer_localite(res["lignes"], dossier_resultats=tmp_path)
    assert (tmp_path / "temps_localite.png").stat().st_size > 0
    assert fichier.endswith("temps_localite.png")
    assert plt.get_fignums() == []
    assert "originale" in formater_localite(res["lignes"])


def test_algos_de_b_mesures_partent_tous_du_meme_sommet():
    g = generer_graphe_mesure(30, 90, graine=1)

    # meme source pour bfs et dijkstra : memes sommets atteints
    dist_bfs, _ = ALGORITHMES["bfs"](g)
    dist_dij, _ = ALGORITHMES["dijkstra"](g)

    assert dist_bfs[g.sommets()[0]] == 0
    assert dist_dij[g.sommets()[0]] == 0
    assert {s for s, d in dist_bfs.items() if d != float("inf")} == {s for s, d in dist_dij.items() if d != float("inf")}


def test_bellman_ford_et_dijkstra_d_accord_sur_un_graphe_mesure():
    g = generer_graphe_mesure(60, 300, graine=4)

    assert ALGORITHMES["bellman_ford"](g)[0] == ALGORITHMES["dijkstra"](g)[0]
