from pathlib import Path

import pytest
from src.cli import main
from src.graphe import Graphe
from src.indicateurs import evaluer_panne_fibre, orchestrer_module_5
from src.io_donnees import charger_jeu_donnees

DOSSIER_DATA = Path(__file__).resolve().parent.parent / "data"


def regle_panne(scenario, u, v):
    return {"scenario": scenario, "action": "fermer_fibre", "u": u, "v": v, "valeur": ""}


def ligne_panne(jeu, dossier_resultats):
    donnees = charger_jeu_donnees(DOSSIER_DATA / jeu)
    return orchestrer_module_5(donnees, dossier_resultats=dossier_resultats)["tableau"][2]


def test_module_5_petit_graphe_resultat_a_la_main(tmp_path):
    ligne = ligne_panne("petit", tmp_path)

    # voir data/petit/resultats_attendus.md
    assert ligne["Composantes Fibre"] == 2
    assert ligne["Coût réparation fibre"] == 9.0


def test_module_5_le_cout_vient_des_donnees(tmp_path):
    # ancien bug : 9.0 etait ecrit en dur quel que soit le jeu
    ligne = ligne_panne("genere", tmp_path)

    assert ligne["Composantes Fibre"] == 2
    assert ligne["Coût réparation fibre"] == 11.2


def test_module_5_panne_hors_de_l_arbre(tmp_path):
    ligne = ligne_panne("realiste", tmp_path)

    assert ligne["Composantes Fibre"] == 1
    assert ligne["Coût réparation fibre"] == 0.0


def test_module_5_ne_modifie_pas_le_graphe_de_base(tmp_path):
    donnees = charger_jeu_donnees(DOSSIER_DATA / "petit")
    avant = donnees["graphe_fibre"].arcs()

    orchestrer_module_5(donnees, dossier_resultats=tmp_path)

    assert donnees["graphe_fibre"].arcs() == avant


def test_panne_fibre_sans_panne_dans_le_scenario():
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 1.0)
    g.ajouter_sommet("Z")

    res = evaluer_panne_fibre(g, [], "aucun")

    assert res == {"nb_composantes": 2, "cout_reparation": 0.0}


def test_panne_fibre_sans_raccordement_cout_infini():
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 1.0)

    res = evaluer_panne_fibre(g, [regle_panne("p", "A", "B")], "p")

    assert res == {"nb_composantes": 2, "cout_reparation": float("inf")}


def test_panne_fibre_ignore_les_autres_scenarios():
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 1.0)

    res = evaluer_panne_fibre(g, [regle_panne("autre", "A", "B")], "p")

    assert res == {"nb_composantes": 1, "cout_reparation": 0.0}


def test_panne_fibre_refuse_plusieurs_pannes_simultanees():
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 1.0)
    g.ajouter_arc("B", "C", 1.0)
    regles = [regle_panne("p", "A", "B"), regle_panne("p", "B", "C")]

    with pytest.raises(ValueError):
        evaluer_panne_fibre(g, regles, "p")


def test_cli_resilience_affiche_le_vrai_cout(capsys, tmp_path, monkeypatch):
    # resultats/ est relatif au dossier courant : on n'ecrase pas celui du projet
    monkeypatch.chdir(tmp_path)

    code = main(["--donnees", str(DOSSIER_DATA / "petit"), "--operation", "resilience"])

    assert code == 0
    assert "9.0" in capsys.readouterr().out
    assert (tmp_path / "resultats" / "tableau_resilience.csv").exists()


def test_module_5_part_des_sites_sensibles(tmp_path):
    donnees = charger_jeu_donnees(DOSSIER_DATA / "petit")
    tableau = orchestrer_module_5(donnees, dossier_resultats=tmp_path)["tableau"]

    # petit graphe : H1 et E1 restent atteignables dans les 3 scenarios
    assert [ligne["Sites sensibles accessibles (%)"] for ligne in tableau] == [100.0, 100.0, 100.0]
    assert "Sites sensibles accessibles (%)" in (tmp_path / "tableau_resilience.md").read_text(encoding="utf-8")


def test_module_5_utilise_les_indicateurs_de_b(tmp_path):
    from src.chemins import comparer_scenario, indicateurs_routes
    from src.indicateurs import appliquer_scenario

    donnees = charger_jeu_donnees(DOSSIER_DATA / "petit")
    ligne = orchestrer_module_5(donnees, dossier_resultats=tmp_path)["tableau"][1]

    g_ref = donnees["graphe_routes"]
    g_sc = appliquer_scenario(g_ref, donnees["scenarios"], nom_scenario="fermeture_route_C1_Q1")
    casernes = ["C1", "C2"]
    attendu = indicateurs_routes(comparer_scenario(g_ref, g_sc, donnees["demandes"], casernes), g_sc, casernes)

    # fermeture de C1 -> Q1 : 2 demandes retardees de 6 min sur 4, soit 3 min en moyenne
    assert ligne["Retard moyen (min)"] == round(attendu["retard_moyen"], 2) == 3.0
    assert ligne["Retard max (min)"] == 6.0
    assert ligne["Demandes inaccessibles"] == attendu["nb_inaccessibles_apres"] == 0


def test_module_5_hopital_coupe(tmp_path):
    donnees = charger_jeu_donnees(DOSSIER_DATA / "petit")
    vers_h1 = [(u, v) for u, v, _ in donnees["graphe_routes"].arcs() if v == "H1"]
    donnees["scenarios"] = [regle_route("coupure_h1", u, v) for u, v in vers_h1]

    ligne = orchestrer_module_5(donnees, dossier_resultats=tmp_path)["tableau"][1]

    # H1 (hopital) n'est plus atteignable : 1 site sensible sur 2
    assert ligne["Sites sensibles accessibles (%)"] == 50.0
    assert ligne["Demandes inaccessibles"] == 1


def regle_route(scenario, u, v):
    return {"scenario": scenario, "action": "fermer_route", "u": u, "v": v, "valeur": ""}
