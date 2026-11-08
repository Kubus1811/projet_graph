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


def test_panne_fibre_plusieurs_pannes_reparees_ensemble():
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 1.0)
    g.ajouter_arc("B", "C", 1.0)
    g.ajouter_arc("C", "D", 1.0)
    g.ajouter_arc("A", "D", 5.0)
    g.ajouter_arc("B", "D", 6.0)
    regles = [regle_panne("p", "A", "B"), regle_panne("p", "C", "D")]

    # l'arbre A-B-C-D perd 2 troncons : {A}, {B, C}, {D}, recolles par A-D puis B-D
    assert evaluer_panne_fibre(g, regles, "p") == {"nb_composantes": 3, "cout_reparation": 11.0}


def test_panne_fibre_plusieurs_pannes_sans_raccordement_cout_infini():
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 1.0)
    g.ajouter_arc("B", "C", 1.0)
    regles = [regle_panne("p", "A", "B"), regle_panne("p", "B", "C")]

    assert evaluer_panne_fibre(g, regles, "p") == {"nb_composantes": 3, "cout_reparation": float("inf")}


def test_cli_resilience_affiche_le_vrai_cout(capsys, tmp_path, monkeypatch):
    # resultats/ est relatif au dossier courant : on n'ecrase pas celui du projet
    monkeypatch.chdir(tmp_path)

    code = main(["--donnees", str(DOSSIER_DATA / "petit"), "--operation", "resilience"])

    assert code == 0
    assert "9.0" in capsys.readouterr().out
    assert (tmp_path / "resultats" / "tableau_resilience_petit.csv").exists()


def test_cli_resilience_un_fichier_par_jeu(tmp_path, monkeypatch):
    # avant, chaque jeu ecrasait le tableau du precedent
    monkeypatch.chdir(tmp_path)

    for jeu in ("petit", "realiste"):
        assert main(["--donnees", str(DOSSIER_DATA / jeu), "--operation", "resilience"]) == 0

    dossier = tmp_path / "resultats"
    assert "fermeture_route_C1_Q1" in (dossier / "tableau_resilience_petit.csv").read_text(encoding="utf-8")
    assert "fermeture_pont_central" in (dossier / "tableau_resilience_realiste.csv").read_text(encoding="utf-8")


def tableau_scenario(jeu, scenario, dossier_resultats):
    donnees = charger_jeu_donnees(DOSSIER_DATA / jeu)
    return orchestrer_module_5(donnees, dossier_resultats=dossier_resultats, nom_jeu=jeu, nom_scenario=scenario)["tableau"]


def test_module_5_compare_le_scenario_demande_a_la_reference(tmp_path):
    tableau = tableau_scenario("petit", "heure_pointe_generale", tmp_path)

    assert len(tableau) == 2
    assert "Situation normale" in tableau[0]["Scénario"]
    assert "heure_pointe_generale" in tableau[1]["Scénario"]
    # heure de pointe du petit jeu : 17 min de retard sur 4 demandes, 7 au pire
    assert tableau[1]["Retard moyen (min)"] == 4.25
    assert tableau[1]["Retard max (min)"] == 7.0


def test_module_5_scenario_de_panne_fibre_laisse_les_routes(tmp_path):
    ligne = tableau_scenario("petit", "panne_fibre_troncon_central", tmp_path)[1]

    assert ligne["Composantes Fibre"] == 2
    assert ligne["Coût réparation fibre"] == 9.0
    assert ligne["Retard max (min)"] == 0.0


def test_module_5_nom_de_scenario_sans_separateur_de_chemin(tmp_path):
    donnees = charger_jeu_donnees(DOSSIER_DATA / "petit")
    donnees["scenarios"] = [regle_route("a/b", "C1", "Q1")]

    orchestrer_module_5(donnees, dossier_resultats=tmp_path, nom_jeu="petit", nom_scenario="a/b")

    assert (tmp_path / "tableau_resilience_petit_a_b.csv").exists()


def test_module_5_scenario_inconnu_refuse(tmp_path):
    with pytest.raises(ValueError, match="nexiste_pas"):
        tableau_scenario("petit", "nexiste_pas", tmp_path)


def test_realiste_fermeture_de_l_axe_critique(tmp_path):
    ligne = tableau_scenario("realiste", "fermeture_axe_CAS_04_QUA_084", tmp_path)[1]

    # test de resistance : 117,5 min cumulees sur 25 demandes, 50,7 min au pire
    assert ligne["Retard moyen (min)"] == 4.7
    assert ligne["Retard max (min)"] == 50.7
    assert ligne["Demandes inaccessibles"] == 0


def test_realiste_panne_d_un_troncon_de_l_arbre(tmp_path):
    ligne = tableau_scenario("realiste", "panne_fibre_CAS_04_QUA_084", tmp_path)[1]

    assert ligne["Composantes Fibre"] == 2
    assert ligne["Coût réparation fibre"] == 40.0


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
