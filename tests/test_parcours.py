import json

import pytest

from src.graphe import Graphe, reconstruire_chemin
from src.io_donnees import charger_jeu_donnees
from src.parcours import (
    dfs, bfs, chemin_min_arcs, accessibilite_multi_sources, trouver_circuit,
    contient_circuit, sites_isoles, sites_non_atteignables,
    composantes_fortement_connexes, composantes_connexes, est_fortement_connexe,
    diagnostic_accessibilite,
)


def graphe_ligne():
    # A -> B -> C -> D, plus E isole
    g = Graphe(oriente=True)
    for s in "ABCDE":
        g.ajouter_sommet(s)
    g.ajouter_arc("A", "B", 1)
    g.ajouter_arc("B", "C", 1)
    g.ajouter_arc("C", "D", 1)
    return g


@pytest.fixture(scope="module")
def petit():
    return charger_jeu_donnees("data/petit")


@pytest.fixture(scope="module")
def attendus():
    with open("data/petit/resultats_attendus.json", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- DFS


def test_dfs_ordre_et_visite_complete():
    g = Graphe(oriente=True)
    g.ajouter_arc("A", "B", 1)
    g.ajouter_arc("A", "C", 1)
    g.ajouter_arc("B", "D", 1)
    g.ajouter_arc("C", "D", 1)
    ordre, pred = dfs(g, "A")
    assert ordre == ["A", "B", "D", "C"]
    assert set(pred) == {"A", "B", "C", "D"}
    assert pred["A"] is None


def test_dfs_respecte_le_sens():
    g = graphe_ligne()
    ordre, _ = dfs(g, "C")
    assert ordre == ["C", "D"]


def test_dfs_pas_de_recursion_sur_long_graphe():
    g = Graphe(oriente=True)
    n = 5000
    for i in range(n - 1):
        g.ajouter_arc(i, i + 1, 1)
    ordre, _ = dfs(g, "0")
    assert len(ordre) == n


def test_source_inexistante():
    g = graphe_ligne()
    with pytest.raises(KeyError):
        dfs(g, "Z")
    with pytest.raises(KeyError):
        bfs(g, "Z")


# ---------------------------------------------------------------- BFS


def test_bfs_petit_jeu(petit, attendus):
    dist, _ = bfs(petit["graphe_routes"], "C1")
    assert dist == attendus["bfs_nombre_arcs_depuis_C1"]


def test_bfs_chemin_min_arcs_different_du_plus_rapide():
    # A->D direct en 1 arc mais lent, A->B->C->D en 3 arcs mais rapide
    g = Graphe(oriente=True)
    g.ajouter_arc("A", "D", 100)
    g.ajouter_arc("A", "B", 1)
    g.ajouter_arc("B", "C", 1)
    g.ajouter_arc("C", "D", 1)
    assert chemin_min_arcs(g, "A", "D") == ["A", "D"]


def test_bfs_non_atteint():
    g = graphe_ligne()
    dist, pred = bfs(g, "A")
    assert dist["D"] == 3
    assert dist["E"] == float("inf")
    assert reconstruire_chemin(pred, "A", "E") is None


def test_arcs_fermes_ignores():
    g = Graphe(oriente=True)
    g.ajouter_arc("A", "B", 1, statut="ferme")
    g.ajouter_arc("A", "C", 1, statut="travaux")
    dist, _ = bfs(g, "A")
    assert dist["B"] == float("inf")
    assert dist["C"] == 1


# ---------------------------------------------------------------- multi-casernes


def test_multi_sources_caserne_origine(petit):
    atteints, _ = accessibilite_multi_sources(petit["graphe_routes"])
    assert len(atteints) == 8
    assert atteints["C1"] == (0, "C1")
    assert atteints["C2"] == (0, "C2")
    assert atteints["Q4"] == (1, "C2")
    assert atteints["Q1"] == (1, "C1")


def test_multi_sources_partiel():
    g = graphe_ligne()
    atteints, _ = accessibilite_multi_sources(g, ["C"])
    assert set(atteints) == {"C", "D"}
    assert sites_non_atteignables(g, ["C"]) == ["A", "B", "E"]


# ---------------------------------------------------------------- circuits


def test_circuit_trouve_est_valide():
    g = Graphe(oriente=True)
    g.ajouter_arc("A", "B", 1)
    g.ajouter_arc("B", "C", 1)
    g.ajouter_arc("C", "D", 1)
    g.ajouter_arc("D", "B", 1)
    circuit = trouver_circuit(g)
    assert circuit[0] == circuit[-1]
    assert set(circuit) == {"B", "C", "D"}
    for u, v in zip(circuit, circuit[1:]):
        assert g.a_arc(u, v)


def test_dag_sans_circuit():
    assert trouver_circuit(graphe_ligne()) is None
    assert not contient_circuit(Graphe(oriente=True))


def test_boucle_est_un_circuit():
    g = Graphe(oriente=True)
    g.ajouter_arc("A", "A", 1)
    assert trouver_circuit(g) == ["A", "A"]


# ---------------------------------------------------------------- isoles


def test_sites_isoles():
    g = graphe_ligne()
    assert sites_isoles(g) == ["E"]
    assert sites_isoles(Graphe(oriente=True)) == []


# ---------------------------------------------------------------- connexite


def test_cfc_kosaraju():
    g = Graphe(oriente=True)
    for u, v in [("A", "B"), ("B", "A"), ("B", "C"), ("C", "D"), ("D", "C"), ("D", "E")]:
        g.ajouter_arc(u, v, 1)
    cfc = sorted(composantes_fortement_connexes(g))
    assert cfc == [["A", "B"], ["C", "D"], ["E"]]
    assert not est_fortement_connexe(g)
    assert len(composantes_connexes(g)) == 1


def test_petit_jeu_fortement_connexe_malgre_sens_unique(petit):
    # Q2 -> Q3 est un sens unique mais on revient par Q3 -> H1 -> Q1 -> Q2
    g = petit["graphe_routes"]
    assert not g.a_arc("Q3", "Q2")
    assert est_fortement_connexe(g)


def test_accessible_mais_pas_fortement_connexe():
    g = graphe_ligne()
    diag = diagnostic_accessibilite(g, ["A"])
    assert diag["nb_atteignables"] == 4
    assert diag["non_atteignables"] == ["E"]
    assert diag["nb_cfc"] == 5
    assert diag["nb_composantes_connexes"] == 2


def test_diagnostic_petit_jeu(petit):
    diag = diagnostic_accessibilite(petit["graphe_routes"])
    assert sorted(diag["casernes"]) == ["C1", "C2"]
    assert diag["non_atteignables"] == []
    assert diag["sensibles_total"] == 2
    assert diag["sensibles_accessibles"] == 2


def test_graphe_vide():
    g = Graphe(oriente=True)
    assert composantes_fortement_connexes(g) == []
    assert composantes_connexes(g) == []
    assert accessibilite_multi_sources(g, []) == ({}, {})
