import csv
import shutil
from pathlib import Path

import pytest
from src.cli import main

DOSSIER_DATA = Path(__file__).resolve().parent.parent / "data"
PETIT = str(DOSSIER_DATA / "petit")
REALISTE = str(DOSSIER_DATA / "realiste")


def lire_csv(chemin):
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_cli_valider_petit():
    assert main(["--donnees", "data/petit", "--operation", "valider"]) == 0


def test_cli_valider_realiste():
    assert main(["--donnees", "data/realiste", "--operation", "valider"]) == 0


def test_cli_resilience_petit():
    assert main(["--donnees", "data/petit", "--operation", "resilience"]) == 0


def test_cli_itineraires_petit():
    assert main(["--donnees", "data/petit", "--operation", "itineraires"]) == 0


def test_cli_generer(tmp_path):
    code = main([
        "--generer",
        "--sommets", "30",
        "--densite", "2.0",
        "--graine", "123",
        "--sortie", str(tmp_path / "cli_test_dir"),
    ])
    assert code == 0
    assert (tmp_path / "cli_test_dir" / "sites.csv").exists()


def test_cli_generer_trop_petit_message_clair(capsys, tmp_path):
    code = main(["--generer", "--sommets", "2", "--sortie", str(tmp_path / "x")])

    assert code == 1
    assert "[ERREUR]" in capsys.readouterr().out


@pytest.mark.parametrize("operation", ["itineraires", "accessibilite", "mst", "panne", "resilience"])
def test_cli_scenario_inconnu_refuse(operation, capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code = main(["--donnees", PETIT, "--scenario", "nexiste_pas", "--operation", operation])

    sortie = capsys.readouterr().out
    assert code == 1
    assert "[ERREUR]" in sortie
    assert "nexiste_pas" in sortie


def test_cli_mst_applique_le_scenario(capsys):
    code = main(["--donnees", PETIT, "--scenario", "panne_fibre_troncon_central", "--operation", "mst"])

    # sans Q2-Q3 (8) l'arbre passe par C2-E1 (9) : 35 - 8 + 9
    assert code == 0
    assert "cout total 36.00" in capsys.readouterr().out


def test_cli_resilience_applique_le_scenario_demande(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code = main(["--donnees", PETIT, "--scenario", "heure_pointe_generale", "--operation", "resilience"])

    lignes = lire_csv(tmp_path / "resultats" / "tableau_resilience_petit_heure_pointe_generale.csv")
    assert code == 0
    assert len(lignes) == 2
    assert lignes[1]["Retard max (min)"] == "7.0"


@pytest.mark.parametrize("operation", ["accessibilite", "mst", "panne", "itineraires", "resilience", "points_faibles"])
def test_cli_dossier_absent_message_clair(operation, capsys, tmp_path):
    code = main(["--donnees", str(tmp_path / "absent"), "--operation", operation])

    assert code == 1
    assert "[ERREUR]" in capsys.readouterr().out


def test_cli_fichier_mal_encode_nomme_le_fichier(capsys, tmp_path):
    jeu = tmp_path / "jeu"
    shutil.copytree(DOSSIER_DATA / "petit", jeu)
    chemin = jeu / "routes.csv"
    chemin.write_bytes(chemin.read_bytes() + "C1,Q1,1,1,fermé\n".encode("latin-1"))

    code = main(["--donnees", str(jeu), "--operation", "itineraires"])

    sortie = capsys.readouterr().out
    assert code == 1
    assert "routes.csv" in sortie


def test_cli_couts_negatifs_refuses_avec_un_message(capsys):
    code = main(["--donnees", str(DOSSIER_DATA / "tests_negatifs"), "--operation", "accessibilite"])

    assert code == 1
    assert "[ERREUR]" in capsys.readouterr().out


@pytest.mark.parametrize("operation", ["valider", "points_faibles"])
def test_cli_scenario_refuse_si_operation_ne_le_gere_pas(operation, capsys):
    code = main(["--donnees", PETIT, "--scenario", "fermeture_route_C1_Q1", "--operation", operation])

    assert code == 1
    assert "--scenario" in capsys.readouterr().out


def test_cli_panne_simultanees_reparees_ensemble(capsys, tmp_path):
    jeu = tmp_path / "jeu"
    shutil.copytree(DOSSIER_DATA / "petit", jeu)
    with open(jeu / "scenarios.csv", "a", encoding="utf-8", newline="") as f:
        f.write("double,fermer_fibre,Q2,Q3,\ndouble,fermer_fibre,Q3,Q4,\n")

    code = main(["--donnees", str(jeu), "--scenario", "double", "--operation", "panne"])

    # il reste {C1,E1,Q1,Q2,H1}, {C2,Q4} et {Q3} : C2-E1 (9) puis H1-Q3 (15)
    sortie = capsys.readouterr().out
    assert code == 0
    assert "24.00" in sortie


def test_cli_points_faibles_ecrit_le_classement(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code = main(["--donnees", PETIT, "--operation", "points_faibles"])

    lignes = lire_csv(tmp_path / "resultats" / "points_faibles_petit.csv")
    routes = [l for l in lignes if l["reseau"] == "route"]
    fibre = [l for l in lignes if l["reseau"] == "fibre"]
    assert code == 0
    # fermer C1 <-> Q1 : D1 et D4 perdent 6 min chacune
    assert (routes[0]["u"], routes[0]["v"]) == ("C1", "Q1")
    assert float(routes[0]["retard_total"]) == 12.0
    # une ligne par troncon de l'arbre du petit graphe
    assert len(fibre) == 7


def test_cli_points_faibles_compare_les_reouvertures(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    code = main(["--donnees", REALISTE, "--operation", "points_faibles"])

    # section 7.3 du rapport : retard cumule restant pour chaque route rouverte
    sortie = capsys.readouterr().out
    assert code == 0
    for valeur in ("118.6", "137.9", "189.4"):
        assert valeur in sortie
