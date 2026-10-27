import pytest
from pathlib import Path
from src.io_donnees import (
    valider_donnees,
    charger_jeu_donnees,
    sauvegarder_sites,
    sauvegarder_routes,
    sauvegarder_demandes,
    charger_sites,
    charger_routes,
    charger_demandes,
    ErreurValidationDonnees,
)


def test_chargement_et_validation_petit_jeu():
    # test du chargement en 1 ligne
    dossier = Path("data/petit")
    est_valide, erreurs = valider_donnees(dossier)
    assert est_valide is True
    assert len(erreurs) == 0

    donnees = charger_jeu_donnees(dossier)
    assert len(donnees["sites"]) == 8
    assert donnees["graphe_routes"].nombre_sommets() == 8
    assert donnees["graphe_fibre"].nombre_sommets() == 8
    assert len(donnees["demandes"]) == 4
    assert len(donnees["scenarios"]) == 4


def test_erreur_identifiant_double(tmp_path):
    f_sites = tmp_path / "sites.csv"
    f_sites.write_text(
        "id,nom,type,longitude,latitude\n"
        "S1,Site 1,quartier,2.3,48.8\n"
        "S1,Site Doublon,ecole,2.4,48.9\n",
        encoding="utf-8"
    )
    (tmp_path / "routes.csv").write_text("u,v,temps_normal,temps_pointe,statut\n", encoding="utf-8")
    (tmp_path / "fibre.csv").write_text("u,v,cost,statut\n", encoding="utf-8")

    est_valide, erreurs = valider_donnees(tmp_path)
    assert est_valide is False
    assert any("identifiant en double 'S1'" in err for err in erreurs)

    with pytest.raises(ErreurValidationDonnees):
        charger_jeu_donnees(tmp_path, valider=True)


def test_erreur_arc_site_inconnu(tmp_path):
    (tmp_path / "sites.csv").write_text(
        "id,nom,type,longitude,latitude\n"
        "S1,Site 1,quartier,2.3,48.8\n",
        encoding="utf-8"
    )
    (tmp_path / "routes.csv").write_text(
        "u,v,temps_normal,temps_pointe,statut\n"
        "S1,S99,10.0,15.0,ouvert\n",
        encoding="utf-8"
    )
    (tmp_path / "fibre.csv").write_text("u,v,cost,statut\n", encoding="utf-8")

    est_valide, erreurs = valider_donnees(tmp_path)
    assert est_valide is False
    assert any("site 'S99' inconnu" in err for err in erreurs)


def test_erreur_colonne_manquante(tmp_path):
    (tmp_path / "sites.csv").write_text(
        "id,nom,type,longitude\n"
        "S1,Site 1,quartier,2.3\n",
        encoding="utf-8"
    )
    (tmp_path / "routes.csv").write_text("u,v,temps_normal,temps_pointe,statut\n", encoding="utf-8")
    (tmp_path / "fibre.csv").write_text("u,v,cost,statut\n", encoding="utf-8")

    est_valide, erreurs = valider_donnees(tmp_path)
    assert est_valide is False
    assert any("colonnes obligatoires manquantes" in err and "latitude" in err for err in erreurs)


def test_erreur_valeur_non_numerique(tmp_path):
    (tmp_path / "sites.csv").write_text(
        "id,nom,type,longitude,latitude\n"
        "S1,Site 1,quartier,2.3,48.8\n"
        "S2,Site 2,quartier,2.4,48.9\n",
        encoding="utf-8"
    )
    (tmp_path / "routes.csv").write_text(
        "u,v,temps_normal,temps_pointe,statut\n"
        "S1,S2,dix_minutes,15.0,ouvert\n",
        encoding="utf-8"
    )
    (tmp_path / "fibre.csv").write_text("u,v,cost,statut\n", encoding="utf-8")

    est_valide, erreurs = valider_donnees(tmp_path)
    assert est_valide is False
    assert any("valeur non numérique 'dix_minutes'" in err for err in erreurs)


def test_erreur_temps_negatif_metier(tmp_path):
    (tmp_path / "sites.csv").write_text(
        "id,nom,type,longitude,latitude\n"
        "S1,Site 1,quartier,2.3,48.8\n"
        "S2,Site 2,quartier,2.4,48.9\n",
        encoding="utf-8"
    )
    (tmp_path / "routes.csv").write_text(
        "u,v,temps_normal,temps_pointe,statut\n"
        "S1,S2,-5.0,10.0,ouvert\n",
        encoding="utf-8"
    )
    (tmp_path / "fibre.csv").write_text("u,v,cost,statut\n", encoding="utf-8")

    # en metier c'est interdit
    est_valide, erreurs = valider_donnees(tmp_path, autoriser_temps_negatifs=False)
    assert est_valide is False
    assert any("temps négatif -5.0 interdit" in err for err in erreurs)

    # autorise seulement pour les tests specifiques de cycle negatif (module 3)
    est_valide_artificiel, err_artificiel = valider_donnees(tmp_path, autoriser_temps_negatifs=True)
    assert est_valide_artificiel is True
    assert len(err_artificiel) == 0


def test_sauvegarde_et_relecture_ronde(tmp_path):
    sites_init = {
        "S1": {"nom": "Alpha", "type": "caserne", "longitude": 1.0, "latitude": 2.0},
        "S2": {"nom": "Beta", "type": "hopital", "longitude": 3.0, "latitude": 4.0},
    }
    sauvegarder_sites(tmp_path / "sites.csv", sites_init)
    sites_lus = charger_sites(tmp_path / "sites.csv")
    assert len(sites_lus) == 2
    assert sites_lus["S1"]["nom"] == "Alpha"

    routes_init = [{"u": "S1", "v": "S2", "temps_normal": 6.5, "temps_pointe": 9.0, "statut": "ouvert"}]
    sauvegarder_routes(tmp_path / "routes.csv", routes_init)
    g_routes = charger_routes(tmp_path / "routes.csv")
    assert g_routes.poids_arc("S1", "S2") == 6.5

    demandes_init = [{"id": "D10", "origine": "S1", "type": "feu", "priorite": "haute"}]
    sauvegarder_demandes(tmp_path / "demandes.csv", demandes_init)
    demandes_lues = charger_demandes(tmp_path / "demandes.csv")
    assert len(demandes_lues) == 1
    assert demandes_lues[0]["id"] == "D10"
