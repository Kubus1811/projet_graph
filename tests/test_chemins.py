import json

import pytest

from src.graphe import Graphe, reconstruire_chemin
from src.io_donnees import charger_jeu_donnees
from src.indicateurs import appliquer_scenario
from src.chemins import (
    dijkstra, dijkstra_multi_sources, bellman_ford, bellman_ford_detail,
    floyd_warshall, detecter_circuit_absorbant, decrire_itineraire,
    itineraires_demandes, comparer_scenario, indicateurs_routes,
    comparer_algorithmes, PoidsNegatifErreur,
)

INF = float("inf")


@pytest.fixture(scope="module")
def petit():
    return charger_jeu_donnees("data/petit")


@pytest.fixture(scope="module")
def attendus():
    with open("data/petit/resultats_attendus.json", encoding="utf-8") as f:
        return json.load(f)


def cout_chemin(g, chemin):
    return sum(g.poids_arc(u, v) for u, v in zip(chemin, chemin[1:]))


def graphe_negatif_sans_circuit():
    g = Graphe(oriente=True)
    g.ajouter_arc("S", "A", 4)
    g.ajouter_arc("S", "B", 5)
    g.ajouter_arc("B", "A", -3)
    g.ajouter_arc("A", "C", 2)
    return g


def graphe_circuit_absorbant():
    # S -> A -> B -> C -> A avec A->B->C->A = -1, et D hors de portee
    g = Graphe(oriente=True)
    g.ajouter_arc("S", "A", 1)
    g.ajouter_arc("A", "B", 2)
    g.ajouter_arc("B", "C", 3)
    g.ajouter_arc("C", "A", -6)
    g.ajouter_arc("C", "E", 1)
    g.ajouter_sommet("D")
    return g


# ---------------------------------------------------------------- petit jeu de reference


@pytest.mark.parametrize("algo", ["dijkstra", "bellman_ford", "floyd_warshall"])
@pytest.mark.parametrize("source", ["C1", "C2"])
def test_distances_petit_jeu(petit, attendus, algo, source):
    g = petit["graphe_routes"]
    if algo == "dijkstra":
        dist, pred = dijkstra(g, source)
    elif algo == "bellman_ford":
        dist, pred = bellman_ford(g, source)
    else:
        d, p = floyd_warshall(g)
        dist, pred = d[source], p[source]

    for cible, att in attendus["plus_courts_chemins_temps_normal"][f"source_{source}"].items():
        assert dist[cible] == pytest.approx(att["distance"])
        chemin = reconstruire_chemin(pred, source, cible)
        # en cas d'egalite le chemin peut differer, mais doit etre valide et de meme cout
        assert chemin[0] == source and chemin[-1] == cible
        assert cout_chemin(g, chemin) == pytest.approx(att["distance"])


def test_chemin_unique_petit_jeu(petit):
    dist, pred = dijkstra(petit["graphe_routes"], "C2")
    assert reconstruire_chemin(pred, "C2", "H1") == ["C2", "Q4", "Q3", "H1"]


def test_scenario_fermeture_petit_jeu(petit, attendus):
    att = attendus["scenario_fermeture_C1_Q1"]["impact_sur_C1_vers_Q1"]
    g_ref = petit["graphe_routes"]
    g_sc = appliquer_scenario(g_ref, petit["scenarios"], "fermeture_route_C1_Q1")

    d_avant, _ = dijkstra(g_ref, "C1")
    d_apres, pred = dijkstra(g_sc, "C1")
    assert d_avant["Q1"] == att["avant"]
    assert d_apres["Q1"] == att["apres"]
    assert reconstruire_chemin(pred, "C1", "Q1") == att["chemin_apres"]
    # le graphe de reference n'a pas bouge
    assert g_ref.a_arc("C1", "Q1")


# ---------------------------------------------------------------- Dijkstra


def test_dijkstra_refuse_poids_negatif():
    with pytest.raises(PoidsNegatifErreur, match="B -> A"):
        dijkstra(graphe_negatif_sans_circuit(), "S")


def test_dijkstra_source_inexistante(petit):
    with pytest.raises(KeyError):
        dijkstra(petit["graphe_routes"], "S99")


def test_dijkstra_inaccessible_et_isole():
    g = Graphe(oriente=True)
    g.ajouter_arc("A", "B", 2)
    g.ajouter_sommet("C")
    dist, pred = dijkstra(g, "B")
    assert dist == {"A": INF, "B": 0.0, "C": INF}
    assert reconstruire_chemin(pred, "B", "A") is None


def test_dijkstra_ignore_routes_fermees():
    g = Graphe(oriente=True)
    g.ajouter_arc("A", "B", 1, statut="ferme")
    g.ajouter_arc("A", "C", 2, statut="ouvert")
    g.ajouter_arc("C", "B", 2, statut="travaux")
    dist, pred = dijkstra(g, "A")
    assert dist["B"] == 4
    it = decrire_itineraire(g, dist, pred, "A", "B")
    assert it["chemin"] == ["A", "C", "B"]
    assert it["nb_arcs"] == 2
    assert it["fermetures"] == [("C", "B", "travaux")]


def test_dijkstra_toutes_routes_fermees():
    g = Graphe(oriente=True)
    g.ajouter_arc("A", "B", 1, statut="ferme")
    dist, _ = dijkstra(g, "A")
    assert dist["B"] == INF


def test_multi_sources_caserne_plus_proche(petit):
    dist, _, origine = dijkstra_multi_sources(petit["graphe_routes"], ["C1", "C2"])
    assert origine["Q1"] == "C1" and dist["Q1"] == 4
    assert origine["Q3"] == "C2" and dist["Q3"] == 5
    assert origine["E1"] == "C1" and dist["E1"] == 5


# ---------------------------------------------------------------- Bellman-Ford


def test_bellman_ford_poids_negatifs_sans_circuit():
    dist, pred = bellman_ford(graphe_negatif_sans_circuit(), "S")
    assert dist["A"] == 2
    assert dist["C"] == 4
    assert reconstruire_chemin(pred, "S", "C") == ["S", "B", "A", "C"]


def test_bellman_ford_arret_anticipe():
    g = Graphe(oriente=True)
    for i in range(50):
        g.ajouter_arc(i, i + 1, 1)
    res = bellman_ford_detail(g, "0")
    assert res["nb_passes"] < 50
    assert not res["circuit_absorbant"]


def test_bellman_ford_circuit_absorbant_moins_infini():
    res = bellman_ford_detail(graphe_circuit_absorbant(), "S")
    d = res["dist"]
    assert res["circuit_absorbant"]
    assert d["S"] == 0
    for s in ("A", "B", "C", "E"):
        assert d[s] == float("-inf")
    assert d["D"] == INF


def test_bellman_ford_circuit_non_accessible():
    # depuis D on ne voit pas le circuit
    res = bellman_ford_detail(graphe_circuit_absorbant(), "D")
    assert not res["circuit_absorbant"]
    assert detecter_circuit_absorbant(graphe_circuit_absorbant())


def test_jeu_circuit_absorbant_accessible():
    # circuit S2 -> S3 -> S4 -> S2 de cout -1, accessible depuis S1
    donnees = charger_jeu_donnees("data/absorbants/accessible", autoriser_temps_negatifs=True)
    g = donnees["graphe_routes"]
    dist, _ = bellman_ford(g, "S1")
    assert dist["S1"] == 0
    assert all(dist[s] == float("-inf") for s in ("S2", "S3", "S4", "S5"))
    assert dist["S6"] == 4 and dist["S7"] == 6
    assert dist["S8"] == INF


# ---------------------------------------------------------------- Floyd-Warshall


def test_floyd_warshall_poids_negatifs():
    dist, pred = floyd_warshall(graphe_negatif_sans_circuit())
    assert dist["S"]["C"] == 4
    assert reconstruire_chemin(pred["S"], "S", "C") == ["S", "B", "A", "C"]
    assert dist["C"]["S"] == INF


def test_floyd_warshall_circuit_absorbant():
    dist, _ = floyd_warshall(graphe_circuit_absorbant())
    assert dist["A"]["A"] < 0
    assert dist["S"]["E"] == float("-inf")
    assert dist["D"]["A"] == INF
    assert dist["S"]["S"] == 0


# ---------------------------------------------------------------- itineraires et scenarios


def test_itineraires_demandes_petit_jeu(petit):
    its = {it["demande"]: it for it in itineraires_demandes(petit["graphe_routes"], petit["demandes"])}
    assert its["D1"]["caserne"] == "C1" and its["D1"]["duree"] == 4
    assert its["D2"]["caserne"] == "C2" and its["D2"]["chemin"] == ["C2", "Q4", "Q3"]
    assert its["D3"]["caserne"] == "C1" and its["D3"]["duree"] == 5
    assert its["D4"]["caserne"] == "C1" and its["D4"]["duree"] == 7
    assert all(it["accessible"] for it in its.values())


def test_comparer_scenario_petit_jeu(petit):
    g_ref = petit["graphe_routes"]
    g_sc = appliquer_scenario(g_ref, petit["scenarios"], "fermeture_route_C1_Q1")
    lignes = {l["demande"]: l for l in comparer_scenario(g_ref, g_sc, petit["demandes"])}

    d1 = lignes["D1"]
    assert d1["cout_avant"] == 4 and d1["cout_apres"] == 10
    assert d1["retard_absolu"] == 6
    assert d1["retard_relatif"] == pytest.approx(1.5)
    assert d1["fermetures_rencontrees"] == [("C1", "Q1")]
    assert d1["chemin_apres"] == ["C1", "E1", "Q2", "Q1"]

    # D4 (H1) : C1 -> Q1 -> H1 = 7 avant, C1 -> E1 -> Q2 -> Q1 -> H1 = 13 apres
    assert lignes["D4"]["retard_absolu"] == 6
    # D2 et D3 ne passent pas par C1 -> Q1
    assert lignes["D2"]["retard_absolu"] == 0
    assert lignes["D3"]["retard_absolu"] == 0

    ind = indicateurs_routes(list(lignes.values()), g_sc)
    assert ind["demandes_devenues_inaccessibles"] == []
    assert ind["retard_max"] == 6
    assert ind["retard_moyen"] == pytest.approx(3.0)
    assert ind["proportion_sensibles_accessibles"] == 1.0


def test_comparer_scenario_demande_devenue_inaccessible():
    g = Graphe(oriente=True)
    g.ajouter_sommet("C", type="caserne")
    g.ajouter_sommet("X", type="hopital")
    g.ajouter_arc("C", "X", 3)
    g_sc = g.copie()
    g_sc.supprimer_arc("C", "X")
    demandes = [{"id": "D", "origine": "X"}]
    lignes = comparer_scenario(g, g_sc, demandes)
    assert lignes[0]["accessible_apres"] is False
    assert lignes[0]["retard_absolu"] is None
    ind = indicateurs_routes(lignes, g_sc)
    assert ind["demandes_devenues_inaccessibles"] == ["D"]
    assert ind["proportion_sensibles_accessibles"] == 0.0


# ---------------------------------------------------------------- comparaison des 3 algos


def test_trois_algos_identiques_petit(petit):
    assert comparer_algorithmes(petit["graphe_routes"]) == []


def test_trois_algos_identiques_realiste():
    g = charger_jeu_donnees("data/realiste")["graphe_routes"]
    assert comparer_algorithmes(g, sources=g.sommets()[:15]) == []


def test_trois_algos_identiques_heure_pointe(petit):
    g = appliquer_scenario(petit["graphe_routes"], petit["scenarios"], "heure_pointe_generale")
    assert comparer_algorithmes(g) == []


def test_dijkstra_bellman_ford_identiques_genere():
    g = charger_jeu_donnees("data/genere")["graphe_routes"]
    assert comparer_algorithmes(g, sources=g.sommets()[:3], avec_floyd=False) == []
