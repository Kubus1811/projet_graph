from pathlib import Path
from src.graphe import Graphe
from src.io_donnees import charger_jeu_donnees
from src.indicateurs import appliquer_scenario, orchestrer_module_5


def test_appliquer_scenario_immutabilite():
    g = Graphe(oriente=True)
    g.ajouter_arc("A", "B", 10.0, temps_normal=10.0, temps_pointe=20.0)
    g.ajouter_arc("B", "C", 5.0, temps_normal=5.0, temps_pointe=8.0)

    regles = [
        {"scenario": "coupure", "action": "fermer_route", "u": "A", "v": "B", "valeur": ""},
        {"scenario": "ralentissement", "action": "modifier_temps", "u": "B", "v": "C", "valeur": "15.0"},
    ]

    g_perturbe = appliquer_scenario(g, regles, nom_scenario="coupure")

    # modifie sur la copie
    assert g_perturbe.a_arc("A", "B") is False
    assert g_perturbe.a_arc("B", "C") is True
    assert g_perturbe.poids_arc("B", "C") == 5.0

    # l'original n'a pas bouge
    assert g.a_arc("A", "B") is True
    assert g.poids_arc("A", "B") == 10.0
    assert g.poids_arc("B", "C") == 5.0


def test_scenario_heure_pointe():
    g = Graphe(oriente=True)
    g.ajouter_arc("A", "B", 10.0, temps_normal=10.0, temps_pointe=25.0)

    regles = [{"scenario": "pointe", "action": "heure_pointe", "u": "", "v": "", "valeur": ""}]
    g_pointe = appliquer_scenario(g, regles, nom_scenario="pointe")

    assert g_pointe.poids_arc("A", "B") == 25.0
    assert g.poids_arc("A", "B") == 10.0


def test_orchestration_module_5_petit_jeu(tmp_path):
    donnees = charger_jeu_donnees("data/petit")
    res = orchestrer_module_5(donnees, dossier_resultats=tmp_path)

    assert "tableau" in res
    assert len(res["tableau"]) == 3
    noms_scenarios = [r["Scénario"] for r in res["tableau"]]
    assert any("Situation normale" in s for s in noms_scenarios)
    assert any("Fermeture" in s for s in noms_scenarios)
    assert any("Panne fibre" in s for s in noms_scenarios)

    assert (tmp_path / "tableau_resilience.md").exists()
    assert (tmp_path / "tableau_resilience.csv").exists()
