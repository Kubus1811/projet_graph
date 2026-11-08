import itertools
import json
import random
from pathlib import Path

import pytest
from src.io_donnees import charger_jeu_donnees, valider_donnees

DOSSIER_NEGATIFS = Path(__file__).resolve().parent.parent / "data" / "absorbants"

CAS = [
    ("accessible", "S1"),
    ("accessible", "S5"),
    ("non_accessible", "S1"),
    ("non_accessible", "S4"),
]


def charger_routes(jeu):
    return charger_jeu_donnees(DOSSIER_NEGATIFS / jeu, autoriser_temps_negatifs=True)["graphe_routes"]


def charger_attendu(jeu):
    with open(DOSSIER_NEGATIFS / jeu / "resultats_attendus.json", encoding="utf-8") as f:
        return json.load(f)


# Les fonctions suivantes verifient les jeux par force brute, sans Bellman-Ford :
# les reponses attendues ne dependent donc pas du code qu'elles serviront a tester.

def atteignables(g, source):
    vus = {source}
    pile = [source]
    while pile:
        for v, _ in g.successeurs(pile.pop()):
            if v not in vus:
                vus.add(v)
                pile.append(v)
    return vus


def circuits_negatifs(g):
    circuits = []
    sommets = sorted(g.sommets())
    for taille in range(1, len(sommets) + 1):
        for circuit in itertools.permutations(sommets, taille):
            # un circuit n'est compte qu'une fois : il commence par son plus petit sommet
            if circuit[0] != min(circuit):
                continue
            couts = [g.poids_arc(u, v) for u, v in zip(circuit, circuit[1:] + circuit[:1])]
            if None not in couts and sum(couts) < 0:
                circuits.append((list(circuit), sum(couts)))
    return circuits


def meilleur_chemin_simple(g, source, cible):
    meilleur = float("inf")
    pile = [(source, 0.0, {source})]
    while pile:
        u, cout, vus = pile.pop()
        if u == cible:
            meilleur = min(meilleur, cout)
        for v, poids in g.successeurs(u):
            if v not in vus:
                pile.append((v, cout + poids, vus | {v}))
    return meilleur


def distances_force_brute(g, source):
    accessibles = atteignables(g, source)

    diminuables = set()
    for circuit, _ in circuits_negatifs(g):
        if circuit[0] in accessibles:
            diminuables |= atteignables(g, circuit[0])

    distances = {}
    for s in g.sommets():
        if s in diminuables:
            distances[s] = float("-inf")
        elif s in accessibles:
            distances[s] = meilleur_chemin_simple(g, source, s)
        else:
            distances[s] = float("inf")
    return distances


@pytest.mark.parametrize("jeu", ["accessible", "non_accessible"])
def test_jeu_refuse_par_la_validation_par_defaut(jeu):
    est_valide, erreurs = valider_donnees(DOSSIER_NEGATIFS / jeu)

    assert est_valide is False
    assert all("négatif" in e for e in erreurs)


@pytest.mark.parametrize("jeu", ["accessible", "non_accessible"])
def test_jeu_accepte_si_temps_negatifs_autorises(jeu):
    assert valider_donnees(DOSSIER_NEGATIFS / jeu, autoriser_temps_negatifs=True) == (True, [])


@pytest.mark.parametrize("jeu", ["accessible", "non_accessible"])
def test_jeu_contient_exactement_le_circuit_annonce(jeu):
    attendu = charger_attendu(jeu)

    assert circuits_negatifs(charger_routes(jeu)) == [(attendu["circuit"], attendu["cout_circuit"])]


@pytest.mark.parametrize("jeu", ["accessible", "non_accessible"])
def test_diagonale_fw_attendue_correspond_au_circuit(jeu):
    attendu = charger_attendu(jeu)

    assert attendu["diagonale_fw_negative"] == attendu["circuit"]


@pytest.mark.parametrize("jeu,source", CAS)
def test_accessibilite_du_circuit_depuis_la_source(jeu, source):
    attendu = charger_attendu(jeu)

    accessible = attendu["circuit"][0] in atteignables(charger_routes(jeu), source)

    assert accessible is attendu["sources"][source]["circuit_accessible"]


@pytest.mark.parametrize("jeu,source", CAS)
def test_distances_attendues_verifiees_par_force_brute(jeu, source):
    attendu = charger_attendu(jeu)["sources"][source]["distances"]

    assert distances_force_brute(charger_routes(jeu), source) == {s: float(d) for s, d in attendu.items()}


def test_circuit_non_accessible_depuis_s1_mais_arc_de_sortie_vers_s3():
    g = charger_routes("non_accessible")

    # le piege du jeu : le circuit atteint S3 alors que S1 atteint aussi S3
    assert "S3" in atteignables(g, "S4")
    assert "S3" in atteignables(g, "S1")
    assert "S4" not in atteignables(g, "S1")


# ---- detection avec les algorithmes de B (module 3)

from src.absorbants import (
    analyser_circuits_absorbants,
    circuit_existe,
    formater_circuits_absorbants,
    sommets_sur_un_circuit,
)
from src.cli import main
from src.graphe import Graphe


@pytest.mark.parametrize("jeu,source", CAS)
def test_analyse_donne_les_reponses_attendues(jeu, source):
    attendu = charger_attendu(jeu)
    g = charger_routes(jeu)

    res = analyser_circuits_absorbants(g, [source])

    assert res["circuit_existe"] is True
    assert res["sommets_sur_circuit"] == attendu["diagonale_fw_negative"]
    par_source = res["sources"][source]
    assert par_source["circuit_accessible"] is attendu["sources"][source]["circuit_accessible"]
    assert par_source["distances"] == {s: float(d) for s, d in attendu["sources"][source]["distances"].items()}


def test_circuit_non_accessible_quand_meme_detecte():
    # depuis S1 bellman-ford ne voit rien, la super-source si
    res = analyser_circuits_absorbants(charger_routes("non_accessible"), ["S1"])

    assert res["sources"]["S1"]["circuit_accessible"] is False
    assert res["circuit_existe"] is True


def test_pas_de_circuit_dans_les_donnees_metier():
    g = charger_jeu_donnees(DOSSIER_NEGATIFS.parent / "petit")["graphe_routes"]

    res = analyser_circuits_absorbants(g, ["C1"])

    assert res["circuit_existe"] is False
    assert res["sommets_sur_circuit"] == []
    assert res["sources"]["C1"]["diminuables"] == []


def test_super_source_d_accord_avec_la_force_brute():
    rng = random.Random(2026)
    for _ in range(40):
        g = Graphe(oriente=True)
        sommets = [f"S{i}" for i in range(rng.randint(2, 6))]
        for s in sommets:
            g.ajouter_sommet(s)
        for u, v in itertools.permutations(sommets, 2):
            if rng.random() < 0.35:
                g.ajouter_arc(u, v, float(rng.randint(-4, 6)))

        attendu = bool(circuits_negatifs(g))

        assert circuit_existe(g) is attendu
        assert bool(sommets_sur_un_circuit(g)) is attendu


def test_super_source_ne_modifie_pas_le_graphe():
    g = charger_routes("accessible")
    avant = g.arcs()

    circuit_existe(g)

    assert g.arcs() == avant


def test_sortie_lisible_jamais_de_distance_finie_pour_un_diminuable():
    texte = formater_circuits_absorbants(analyser_circuits_absorbants(charger_routes("accessible"), ["S1"]))

    assert "S5 : -inf (diminuable sans fin)" in texte
    assert "S8 : inf (inaccessible)" in texte
    assert "jeu de test artificiel" in texte


def test_cli_absorbant(capsys):
    code = main(["--donnees", str(DOSSIER_NEGATIFS / "non_accessible"), "--source", "S4", "--operation", "absorbant"])

    sortie = capsys.readouterr().out
    assert code == 0
    assert "Depuis S4 : circuit accessible = oui" in sortie


def test_cli_absorbant_source_inconnue(capsys):
    code = main(["--donnees", str(DOSSIER_NEGATIFS / "accessible"), "--source", "Z9", "--operation", "absorbant"])

    assert code == 1
    assert "[ERREUR]" in capsys.readouterr().out
