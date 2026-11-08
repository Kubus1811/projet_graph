import pytest
from pathlib import Path
from src.arbres import kruskal
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


SITES_OK = (
    "id,nom,type,longitude,latitude\n"
    "S1,Site 1,caserne,2.3,48.8\n"
    "S2,Site 2,quartier,2.4,48.9\n"
    "S3,Site 3,hopital,2.5,48.7\n"
)
ROUTES_OK = "u,v,temps_normal,temps_pointe,statut\nS1,S2,5,8,ouvert\nS2,S3,5,8,ouvert\n"
FIBRE_OK = "u,v,cost,statut\nS1,S2,5,ouvert\nS2,S3,6,ouvert\n"
EN_TETE_SCENARIOS = "scenario,action,u,v,valeur\n"


def ecrire_jeu(dossier, sites=SITES_OK, routes=ROUTES_OK, fibre=FIBRE_OK, scenarios=EN_TETE_SCENARIOS):
    for nom, contenu in (("sites", sites), ("routes", routes), ("fibre", fibre), ("scenarios", scenarios)):
        (dossier / f"{nom}.csv").write_text(contenu, encoding="utf-8")


def erreurs_de_la_ligne(dossier, reference, **options):
    # reference : "routes.csv ligne 4" par exemple
    est_valide, erreurs = valider_donnees(dossier, **options)
    assert est_valide is False
    return [e for e in erreurs if reference in e]


def test_jeu_de_reference_valide(tmp_path):
    # sert de base aux tests suivants : seule la ligne ajoutee peut les faire echouer
    ecrire_jeu(tmp_path)

    assert valider_donnees(tmp_path) == (True, [])


@pytest.mark.parametrize("valeur", ["nan", "inf", "-inf"])
def test_erreur_temps_non_fini(tmp_path, valeur):
    ecrire_jeu(tmp_path, routes=ROUTES_OK + f"S3,S1,{valeur},8,ouvert\n")

    # negatifs autorises : seul le caractere non fini doit etre refuse
    assert erreurs_de_la_ligne(tmp_path, "routes.csv ligne 4", autoriser_temps_negatifs=True)


def test_erreur_cout_fibre_non_fini(tmp_path):
    ecrire_jeu(tmp_path, fibre=FIBRE_OK + "S3,S1,nan,ouvert\n")

    assert erreurs_de_la_ligne(tmp_path, "fibre.csv ligne 4")


def test_erreur_coordonnee_non_finie(tmp_path):
    ecrire_jeu(tmp_path, sites=SITES_OK + "S4,Site 4,quartier,nan,48.9\n")

    assert erreurs_de_la_ligne(tmp_path, "sites.csv ligne 5")


def test_erreur_statut_route_inconnu(tmp_path):
    ecrire_jeu(tmp_path, routes=ROUTES_OK + "S3,S1,5,8,clos\n")

    assert erreurs_de_la_ligne(tmp_path, "routes.csv ligne 4")


def test_erreur_statut_fibre_inconnu(tmp_path):
    ecrire_jeu(tmp_path, fibre=FIBRE_OK + "S3,S1,5,casse\n")

    assert erreurs_de_la_ligne(tmp_path, "fibre.csv ligne 4")


@pytest.mark.parametrize("statut", ["ouvert", "ferme", "travaux", "Fermé", ""])
def test_statuts_autorises(tmp_path, statut):
    ecrire_jeu(tmp_path, routes=ROUTES_OK + f"S3,S1,5,8,{statut}\n")

    assert valider_donnees(tmp_path) == (True, [])


def test_statut_en_majuscules_garde_le_troncon_dans_l_arbre(tmp_path):
    ecrire_jeu(tmp_path, fibre=FIBRE_OK + "S1,S3,2,OUVERT\n")

    fibre = charger_jeu_donnees(tmp_path)["graphe_fibre"]

    assert ("S1", "S3", 2.0) in kruskal(fibre)["aretes"]


def test_statut_de_route_normalise_au_chargement(tmp_path):
    ecrire_jeu(tmp_path, routes=ROUTES_OK + "S3,S1,5,8,FERME\n")

    routes = charger_jeu_donnees(tmp_path)["graphe_routes"]

    assert routes.attributs_arc("S3", "S1")["statut"] == "ferme"


def test_erreur_arc_en_double(tmp_path):
    ecrire_jeu(tmp_path, routes=ROUTES_OK + "S1,S2,99,120,ouvert\n")

    assert erreurs_de_la_ligne(tmp_path, "routes.csv ligne 4")


def test_arcs_de_sens_opposes_autorises(tmp_path):
    # graphe oriente : S2 -> S1 n'est pas un doublon de S1 -> S2
    ecrire_jeu(tmp_path, routes=ROUTES_OK + "S2,S1,5,8,ouvert\n")

    assert valider_donnees(tmp_path) == (True, [])


def test_erreur_troncon_en_double_dans_l_autre_sens(tmp_path):
    # graphe non oriente : S2 - S1 est le meme troncon que S1 - S2
    ecrire_jeu(tmp_path, fibre=FIBRE_OK + "S2,S1,99,ouvert\n")

    assert erreurs_de_la_ligne(tmp_path, "fibre.csv ligne 4")


def test_erreur_temps_pointe_plus_rapide_que_normal(tmp_path):
    ecrire_jeu(tmp_path, routes=ROUTES_OK + "S3,S1,10,2,ouvert\n")

    assert erreurs_de_la_ligne(tmp_path, "routes.csv ligne 4")


def test_temps_pointe_egal_au_normal_autorise(tmp_path):
    ecrire_jeu(tmp_path, routes=ROUTES_OK + "S3,S1,10,10,ouvert\n")

    assert valider_donnees(tmp_path) == (True, [])


@pytest.mark.parametrize("ligne", ["x,fermer_route,S2,S1,", "x,modifier_temps,S2,S1,5"])
def test_erreur_scenario_sur_route_inexistante(tmp_path, ligne):
    # S1 -> S2 existe, pas S2 -> S1 : la route est orientee
    ecrire_jeu(tmp_path, scenarios=EN_TETE_SCENARIOS + ligne + "\n")

    assert erreurs_de_la_ligne(tmp_path, "scenarios.csv ligne 2")


def test_erreur_scenario_sur_troncon_inexistant(tmp_path):
    ecrire_jeu(tmp_path, scenarios=EN_TETE_SCENARIOS + "x,fermer_fibre,S1,S3,\n")

    assert erreurs_de_la_ligne(tmp_path, "scenarios.csv ligne 2")


def test_scenario_sur_troncon_ecrit_dans_l_autre_sens(tmp_path):
    ecrire_jeu(tmp_path, scenarios=EN_TETE_SCENARIOS + "x,fermer_fibre,S2,S1,\n")

    assert valider_donnees(tmp_path) == (True, [])


@pytest.mark.parametrize("action", ["fermer_route", "modifier_temps", "fermer_fibre"])
def test_erreur_scenario_sans_extremites(tmp_path, action):
    ecrire_jeu(tmp_path, scenarios=EN_TETE_SCENARIOS + f"x,{action},,,5\n")

    assert erreurs_de_la_ligne(tmp_path, "scenarios.csv ligne 2")


def test_heure_pointe_sans_extremites_autorisee(tmp_path):
    ecrire_jeu(tmp_path, scenarios=EN_TETE_SCENARIOS + "x,heure_pointe,,,\n")

    assert valider_donnees(tmp_path) == (True, [])


def test_erreur_scenario_sans_nom(tmp_path):
    ecrire_jeu(tmp_path, scenarios=EN_TETE_SCENARIOS + ",fermer_route,S1,S2,\n")

    assert erreurs_de_la_ligne(tmp_path, "scenarios.csv ligne 2")


def test_erreur_scenario_valeur_non_finie(tmp_path):
    ecrire_jeu(tmp_path, scenarios=EN_TETE_SCENARIOS + "x,modifier_temps,S1,S2,nan\n")

    assert erreurs_de_la_ligne(tmp_path, "scenarios.csv ligne 2")
