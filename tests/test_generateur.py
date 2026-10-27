import filecmp
import time
from pathlib import Path
from src.generateur import generer_jeu_donnees
from src.io_donnees import valider_donnees, charger_jeu_donnees


def test_generateur_reproductibilite_graine(tmp_path):
    dossier_1 = tmp_path / "run_1"
    dossier_2 = tmp_path / "run_2"
    dossier_diff = tmp_path / "run_diff"

    # meme graine => fichiers identiques au bit pres
    generer_jeu_donnees(n_sommets=50, densite=2.5, graine=12345, dossier_sortie=dossier_1)
    generer_jeu_donnees(n_sommets=50, densite=2.5, graine=12345, dossier_sortie=dossier_2)
    generer_jeu_donnees(n_sommets=50, densite=2.5, graine=99999, dossier_sortie=dossier_diff)

    fichiers = ["sites.csv", "routes.csv", "fibre.csv", "demandes.csv", "scenarios.csv"]
    for f in fichiers:
        assert filecmp.cmp(dossier_1 / f, dossier_2 / f, shallow=False)

    assert not filecmp.cmp(dossier_1 / "routes.csv", dossier_diff / "routes.csv", shallow=False)


def test_generateur_validation_conforme(tmp_path):
    dossier = tmp_path / "test_valid"
    generer_jeu_donnees(n_sommets=60, densite=3.0, graine=42, dossier_sortie=dossier)

    est_valide, erreurs = valider_donnees(dossier)
    assert est_valide is True
    assert len(erreurs) == 0

    donnees = charger_jeu_donnees(dossier)
    assert donnees["graphe_routes"].nombre_sommets() == 60
    assert donnees["graphe_fibre"].nombre_sommets() == 60


def test_generateur_performance_1000_sommets(tmp_path):
    dossier = tmp_path / "genere_1000"
    t0 = time.perf_counter()
    info = generer_jeu_donnees(n_sommets=1000, densite=3.0, graine=777, dossier_sortie=dossier)
    t1 = time.perf_counter()

    duree = t1 - t0
    # doit tourner en moins de 5 secondes
    assert duree < 5.0
    assert info["n_sommets"] == 1000

    est_valide, erreurs = valider_donnees(dossier)
    assert est_valide is True
    assert len(erreurs) == 0
