import pytest
from src.graphe import Graphe, reconstruire_chemin


def test_graphe_oriente():
    g = Graphe(oriente=True)
    g.ajouter_sommet("A", nom="Sommet A", type="caserne")
    g.ajouter_sommet("B", nom="Sommet B", type="hopital")
    g.ajouter_arc("A", "B", 12.5, type_voie="avenue")

    assert g.oriente is True
    assert g.nombre_sommets() == 2
    assert "A" in g and "B" in g
    assert g.a_arc("A", "B") is True
    assert g.a_arc("B", "A") is False
    assert g.poids_arc("A", "B") == 12.5
    assert g.successeurs("A") == [("B", 12.5)]
    assert g.successeurs("B") == []


def test_graphe_non_oriente():
    g = Graphe(oriente=False)
    g.ajouter_arc("X", "Y", 7.0)

    assert g.oriente is False
    assert g.nombre_sommets() == 2
    assert g.a_arc("X", "Y") is True
    assert g.a_arc("Y", "X") is True
    assert g.successeurs("X") == [("Y", 7.0)]
    assert g.successeurs("Y") == [("X", 7.0)]
    # verif aretes uniques pour kruskal
    aretes_uniques = g.arcs(uniques_si_non_oriente=True)
    assert len(aretes_uniques) == 1
    assert aretes_uniques[0][2] == 7.0
    assert len(g.arcs(uniques_si_non_oriente=False)) == 2


def test_copie_profonde_isolation():
    g = Graphe(oriente=True)
    g.ajouter_arc("S1", "S2", 10.0)
    g.ajouter_sommet("S1", capacite=5)

    copie = g.copie()

    # on modifie la copie
    copie.ajouter_sommet("S3")
    copie.ajouter_arc("S1", "S3", 4.0)
    copie.modifier_poids_arc("S1", "S2", 99.0)
    copie.supprimer_arc("S1", "S2")

    # le graphe initial ne doit pas avoir bouge
    assert "S3" not in g
    assert g.a_arc("S1", "S2") is True
    assert g.poids_arc("S1", "S2") == 10.0
    assert len(g.sommets()) == 2
    assert len(copie.sommets()) == 3
    assert copie.a_arc("S1", "S2") is False


def test_suppression_et_modification_arcs():
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 5.0)
    assert g.poids_arc("A", "B") == 5.0
    assert g.poids_arc("B", "A") == 5.0

    assert g.modifier_poids_arc("A", "B", 15.0) is True
    assert g.poids_arc("A", "B") == 15.0
    assert g.poids_arc("B", "A") == 15.0

    assert g.supprimer_arc("A", "B") is True
    assert g.a_arc("A", "B") is False
    assert g.a_arc("B", "A") is False
    assert g.supprimer_arc("A", "B") is False


def test_reconstruire_chemin():
    # S -> A -> B -> C
    pred = {"S": None, "A": "S", "B": "A", "C": "B", "D": None}

    chemin = reconstruire_chemin(pred, "S", "C")
    assert chemin == ["S", "A", "B", "C"]

    assert reconstruire_chemin(pred, "S", "S") == ["S"]
    assert reconstruire_chemin(pred, "S", "D") is None
    assert reconstruire_chemin(pred, "S", "INCONNU") is None

    # securite si cycle infini dans pred
    pred_cyclique = {"A": "B", "B": "A"}
    assert reconstruire_chemin(pred_cyclique, "S", "A") is None
