import itertools
import json
import random
import threading
import urllib.error
import urllib.request

import pytest
from src import salle_de_crise
from src.arbres import analyser_panne, kruskal, reparer_pannes
from src.graphe import Graphe
from src.salle_de_crise import carte, points_faibles, simuler
from src.site_web import creer_serveur


def par_id(resultat):
    return {d["id"]: d for d in resultat["demandes"]}


def test_situation_normale_sans_retard():
    res = simuler("petit")

    assert res["indicateurs"]["inaccessibles"] == 0
    assert res["indicateurs"]["retard_moyen"] == 0.0
    assert res["indicateurs"]["cout_reparation"] == 0.0
    assert res["indicateurs"]["composantes_fibre"] == 1
    assert res["indicateurs"]["cout_arbre"] == 35.0


def test_fermeture_c1_q1_resultat_a_la_main():
    res = simuler("petit", routes_fermees=[["C1", "Q1"]])

    d1 = par_id(res)["D1"]
    # voir data/petit/resultats_attendus.md
    assert d1["temps_avant"] == 4.0
    assert d1["temps_apres"] == 10.0
    assert d1["retard"] == 6.0
    assert d1["retard_relatif"] == 1.5
    assert d1["chemin"] == ["C1", "E1", "Q2", "Q1"]
    assert d1["nb_arcs"] == 3
    assert res["indicateurs"]["retard_max"] == 6.0


def test_retard_moyen_sur_toutes_les_demandes_accessibles():
    # 2 demandes retardees de 6 min sur 4 : le temps moyen passe de 5,25 a 8,25
    res = simuler("petit", routes_fermees=[["C1", "Q1"]])

    assert res["indicateurs"]["retard_moyen"] == 3.0


def test_demande_devenue_inaccessible():
    routes = salle_de_crise._charger("petit")["routes"]
    res = simuler("petit", routes_fermees=[[u, v] for u, v, _ in routes.arcs()])

    assert res["indicateurs"]["inaccessibles"] == res["indicateurs"]["total_demandes"]
    assert res["indicateurs"]["part_sites_sensibles"] == 0.0
    assert res["indicateurs"]["retard_moyen"] == 0.0
    for d in res["demandes"]:
        assert d["accessible"] is False
        assert d["chemin"] is None
        assert d["retard"] is None


def test_heure_de_pointe_rallonge_les_trajets():
    res = simuler("petit", pointe=True)

    assert res["indicateurs"]["retard_max"] > 0
    assert all(d["retard"] >= 0 for d in res["demandes"])


def test_temps_modifie():
    res = simuler("petit", temps_modifies=[["C1", "Q1", 7.0]])

    assert par_id(res)["D1"]["temps_apres"] == 7.0


def test_panne_fibre_resultat_a_la_main():
    res = simuler("petit", fibres_en_panne=[["Q3", "Q2"]])

    assert res["indicateurs"]["composantes_fibre"] == 2
    assert res["indicateurs"]["composantes_fibre_apres_reparation"] == 1
    assert res["indicateurs"]["cout_reparation"] == 9.0
    assert res["indicateurs"]["cout_arbre"] == 36.0
    assert res["fibre"]["raccordements"] == [("C2", "E1", 9.0)]


def test_la_simulation_ne_modifie_jamais_le_jeu_de_base():
    jeu = salle_de_crise._charger("petit")
    avant = (jeu["routes"].arcs(), jeu["fibre"].arcs())

    simuler("petit", routes_fermees=[["C1", "Q1"]], fibres_en_panne=[["Q2", "Q3"]],
            temps_modifies=[["C1", "E1", 50.0]], pointe=True)

    assert (jeu["routes"].arcs(), jeu["fibre"].arcs()) == avant
    assert simuler("petit")["indicateurs"]["retard_max"] == 0.0


@pytest.mark.parametrize("nom", ["inconnu", "../petit", "", "tests_negatifs"])
def test_jeu_hors_de_la_liste_refuse(nom):
    with pytest.raises(ValueError):
        simuler(nom)


@pytest.mark.parametrize("arguments", [
    {"routes_fermees": [["C1", "Z9"]]},
    {"temps_modifies": [["C1", "Z9", 3.0]]},
    {"fibres_en_panne": [["C1", "Z9"]]},
])
def test_troncon_inexistant_refuse(arguments):
    with pytest.raises(ValueError):
        simuler("petit", **arguments)


def test_resultat_sans_infini_pour_le_json():
    routes = salle_de_crise._charger("petit")["routes"]
    res = simuler("petit", routes_fermees=[[u, v] for u, v, _ in routes.arcs()])

    json.dumps(res, allow_nan=False)


@pytest.mark.parametrize("nom", list(salle_de_crise.JEUX))
def test_carte_coherente(nom):
    donnees = carte(nom)
    ids = {s["id"] for s in donnees["sites"]}

    assert all(r["u"] in ids and r["v"] in ids for r in donnees["routes"])
    assert all(t["u"] < t["v"] and t["u"] in ids and t["v"] in ids for t in donnees["fibre"])
    assert donnees["scenarios"]


def test_scenarios_du_csv_traduits():
    scenarios = {s["nom"]: s for s in carte("realiste")["scenarios"]}

    assert scenarios["fermeture_pont_central"]["routes_fermees"] == [["CAS_01", "HOP_01"], ["HOP_01", "CAS_01"]]
    assert scenarios["panne_fibre_backbone_sud"]["fibres_en_panne"] == [["TEL_01", "TEL_02"]]
    assert scenarios["heure_pointe_generale"]["pointe"] is True
    assert scenarios["travaux_boulevard_est"]["temps_modifies"] == [["CAS_04", "TEL_04", 35.0]]


@pytest.mark.parametrize("nom", list(salle_de_crise.JEUX))
def test_tous_les_scenarios_du_csv_se_simulent(nom):
    for sc in carte(nom)["scenarios"]:
        simuler(nom, sc["routes_fermees"], sc["fibres_en_panne"], sc["temps_modifies"], sc["pointe"])


def test_points_faibles_routes_identiques_a_la_force_brute():
    # meme classement en coupant tous les axes, y compris ceux sans itineraire
    routes = salle_de_crise._charger("petit")["routes"]
    axes = {(min(u, v), max(u, v)) for u, v, _ in routes.arcs()}
    attendu = []
    for a, b in axes:
        fermes = [[u, v] for u, v in ((a, b), (b, a)) if routes.a_arc(u, v)]
        lignes = simuler("petit", routes_fermees=fermes)["demandes"]
        inaccessibles = sum(1 for d in lignes if not d["accessible"])
        retard = sum(d["retard"] for d in lignes if d["retard"])
        if inaccessibles or retard:
            attendu.append((-inaccessibles, -retard, a, b))
    attendu.sort()

    res = points_faibles("petit", limite=1000)["routes"]

    assert [(-r["inaccessibles"], -r["retard_total"], r["u"], r["v"]) for r in res] == attendu


def test_points_faibles_fibre_met_les_troncons_sans_secours_en_tete():
    res = points_faibles("realiste", limite=2)["fibre"]

    # identifies a la main avec analyser_panne sur tout l'arbre
    assert {(t["u"], t["v"]) for t in res} == {("ECO_05", "QUA_074"), ("QUA_074", "QUA_084")}
    assert all(t["raccordable"] is False and t["surcout"] is None for t in res)


def test_points_faibles_respecte_la_limite():
    res = points_faibles("realiste", limite=3)

    assert len(res["routes"]) <= 3
    assert len(res["fibre"]) == 3


def test_points_faibles_garde_le_classement_complet_pour_la_carte():
    res = points_faibles("realiste", limite=3)

    assert res["routes_toutes"][:3] == res["routes"]
    assert res["fibre_toutes"][:3] == res["fibre"]
    assert len(res["fibre_toutes"]) == res["nb_troncons_testes"]


def test_temps_de_reponse_resultat_a_la_main():
    temps = simuler("petit")["temps_sites"]

    # voir data/petit/resultats_attendus.md : chaque site prend la caserne la plus proche
    assert temps["C1"] == 0.0
    assert temps["C2"] == 0.0
    assert temps["Q1"] == 4.0
    assert temps["Q4"] == 3.0
    assert temps["H1"] == 7.0


def test_temps_de_reponse_site_coupe_du_reseau():
    routes = salle_de_crise._charger("petit")["routes"]
    temps = simuler("petit", routes_fermees=[[u, v] for u, v, _ in routes.arcs()])["temps_sites"]

    # une caserne reste a 0 d'elle-meme, tout le reste devient inatteignable
    assert temps["C1"] == 0.0
    assert temps["Q1"] is None


def graphe_aleatoire(rng):
    g = Graphe(oriente=False)
    sommets = [f"S{i}" for i in range(rng.randint(3, 15))]
    for s in sommets:
        g.ajouter_sommet(s)
    for u, v in itertools.combinations(sommets, 2):
        if rng.random() < 0.4:
            g.ajouter_arc(u, v, float(rng.randint(1, 9)))
    return g


def test_reparer_une_panne_donne_le_meme_resultat_qu_analyser_panne():
    rng = random.Random(2026)
    for _ in range(30):
        g = graphe_aleatoire(rng)
        for u, v, _ in kruskal(g)["aretes"]:
            attendu = analyser_panne(g, u, v)
            res = reparer_pannes(g, [(u, v)])

            assert res["cout_reparation"] == attendu["cout_reparation"]
            assert res["cout_arbre_apres"] == attendu["cout_arbre_apres"]
            assert res["nb_composantes_panne"] == attendu["nb_composantes_panne"]


def test_reparer_plusieurs_pannes_donne_un_arbre_minimal():
    rng = random.Random(2026)
    for _ in range(40):
        g = graphe_aleatoire(rng)
        aretes = g.arcs()
        pannes = rng.sample(aretes, min(3, len(aretes)))

        res = reparer_pannes(g, [(u, v) for u, v, _ in pannes])

        g_sans = g.copie()
        for u, v, _ in pannes:
            g_sans.supprimer_arc(u, v)
        attendu = kruskal(g_sans)
        assert res["cout_arbre_apres"] == attendu["cout_total"]
        assert res["nb_composantes_apres"] == attendu["nb_composantes"]


def test_reparer_panne_hors_de_l_arbre_ne_coute_rien():
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 1.0)
    g.ajouter_arc("B", "C", 1.0)
    g.ajouter_arc("A", "C", 5.0)

    res = reparer_pannes(g, [("A", "C")])

    assert res["cout_reparation"] == 0.0
    assert res["coupees"] == []
    assert res["nb_composantes_panne"] == 1


def test_reparer_n_utilise_pas_un_troncon_indisponible():
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 1.0)
    g.ajouter_arc("A", "C", 2.0)
    g.ajouter_arc("B", "C", 3.0, statut="travaux")

    res = reparer_pannes(g, [("A", "C")])

    assert res["raccordements"] == []
    assert res["nb_composantes_apres"] == 2


@pytest.fixture(scope="module")
def adresse():
    serveur = creer_serveur(port=0)
    fil = threading.Thread(target=serveur.serve_forever, daemon=True)
    fil.start()
    yield f"http://127.0.0.1:{serveur.server_address[1]}"
    serveur.shutdown()
    serveur.server_close()


def lire(url, donnees=None):
    corps = json.dumps(donnees).encode("utf-8") if donnees is not None else None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=corps)) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_serveur_ecoute_seulement_sur_cet_ordinateur():
    serveur = creer_serveur(port=0)
    try:
        assert serveur.server_address[0] == "127.0.0.1"
    finally:
        serveur.server_close()


def test_serveur_sert_les_deux_pages(adresse):
    code, corps = lire(adresse + "/")
    assert code == 200
    assert "La nuit de l'orage" in corps.decode("utf-8")

    code, corps = lire(adresse + "/salle")
    assert code == 200
    assert "Salle de crise Novapolis" in corps.decode("utf-8")


def test_serveur_sert_l_histoire(adresse):
    code, corps = lire(adresse + "/api/recit")

    assert code == 200
    assert json.loads(corps)["chapitres"]


def test_serveur_carte_et_points_faibles(adresse):
    code, corps = lire(adresse + "/api/carte?jeu=petit")
    assert code == 200
    assert len(json.loads(corps)["sites"]) == 8

    code, corps = lire(adresse + "/api/points_faibles?jeu=petit")
    assert code == 200
    assert "routes" in json.loads(corps)


def test_serveur_simule(adresse):
    code, corps = lire(adresse + "/api/simuler", {"jeu": "petit", "routes_fermees": [["C1", "Q1"]]})

    assert code == 200
    assert json.loads(corps)["indicateurs"]["retard_max"] == 6.0


@pytest.mark.parametrize("chemin,donnees", [
    ("/api/carte?jeu=../secret", None),
    ("/api/simuler", {"jeu": "petit", "routes_fermees": [["C1", "Z9"]]}),
    ("/api/simuler", {"sans_jeu": True}),
])
def test_serveur_refuse_les_mauvaises_demandes(adresse, chemin, donnees):
    code, corps = lire(adresse + chemin, donnees)

    assert code == 400
    assert "erreur" in json.loads(corps)


def test_serveur_page_inconnue(adresse):
    code, _ = lire(adresse + "/secret.txt")

    assert code == 404


def test_meme_regle_que_b_pour_les_routes_en_travaux():
    g = Graphe(oriente=True)
    g.ajouter_arc("A", "B", 1.0, statut="travaux")
    g.ajouter_arc("B", "C", 1.0, statut="ferme")
    g.ajouter_arc("C", "A", 1.0, statut="ouvert")

    res = salle_de_crise._sans_troncons_indisponibles(g, salle_de_crise.arc_ouvert)

    assert res.a_arc("A", "B") is True
    assert res.a_arc("B", "C") is False
    assert res.a_arc("C", "A") is True


def test_fibre_en_travaux_indisponible():
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 1.0, statut="travaux")
    g.ajouter_arc("B", "C", 1.0, statut="ouvert")

    res = salle_de_crise._sans_troncons_indisponibles(g, salle_de_crise._fibre_disponible)

    assert res.a_arc("A", "B") is False
    assert res.a_arc("B", "C") is True


# ---- visualisation de B integree au site

from src.salle_de_crise import analyse_connexite, itineraire_interactif


@pytest.mark.parametrize("algo", ["dijkstra", "bellman_ford", "floyd_warshall"])
def test_itineraire_interactif_resultat_a_la_main(algo):
    res = itineraire_interactif("petit", "C1", "Q1", algo)

    it = res["itineraire"]
    assert it["chemin"] == ["C1", "Q1"]
    assert it["duree"] == 4.0
    assert it["poids"] == [4.0]
    assert it["comparaison"] == {"dijkstra": 4.0, "bellman_ford": 4.0, "floyd_warshall": 4.0}


def test_itineraire_interactif_avec_route_fermee():
    it = itineraire_interactif("petit", "C1", "Q1", routes_fermees=[["C1", "Q1"]])["itineraire"]

    # voir data/petit/resultats_attendus.md
    assert it["chemin"] == ["C1", "E1", "Q2", "Q1"]
    assert it["duree"] == 10.0
    assert it["duree_reference"] == 4.0
    assert sum(it["poids"]) == 10.0


def test_itineraire_interactif_exploration_dans_l_ordre_des_distances():
    res = itineraire_interactif("petit", "C1")

    ordre = [s for s, _ in res["exploration"]]
    distances = itineraire_interactif("petit", "C1", "Q4")["itineraire"]
    assert ordre[0] == "C1"
    assert res["exploration"][0][1] is None
    assert len(ordre) == 8
    assert res["itineraire"] is None
    assert distances["duree"] == 13.0


def test_itineraire_interactif_destination_inaccessible():
    routes = salle_de_crise._charger("petit")["routes"]
    vers_h1 = [[u, v] for u, v, _ in routes.arcs() if v == "H1"]

    it = itineraire_interactif("petit", "C1", "H1", routes_fermees=vers_h1)["itineraire"]

    assert it["accessible"] is False
    assert it["duree"] is None
    assert it["comparaison"] == {"dijkstra": None, "bellman_ford": None, "floyd_warshall": None}


@pytest.mark.parametrize("arguments", [
    {"source": "Z9"},
    {"source": "C1", "cible": "Z9"},
    {"source": "C1", "cible": "Q1", "algo": "inconnu"},
])
def test_itineraire_interactif_refuse_les_mauvaises_demandes(arguments):
    with pytest.raises(ValueError):
        itineraire_interactif("petit", **arguments)


def test_connexite_resultat_a_la_main():
    res = analyse_connexite("petit")

    assert len(res["caserne_par_site"]) == 8
    assert res["non_atteignables"] == []
    assert len(res["cfc"]) == 1
    assert res["sensibles_accessibles"] == res["sensibles_total"] == 2


def test_connexite_site_coupe_apres_fermetures():
    routes = salle_de_crise._charger("petit")["routes"]
    vers_h1 = [[u, v] for u, v, _ in routes.arcs() if v == "H1"]

    res = analyse_connexite("petit", routes_fermees=vers_h1)

    assert res["non_atteignables"] == ["H1"]
    assert res["sensibles_accessibles"] == 1
    assert len(res["cfc"]) > 1


def test_serveur_chemin_et_connexite(adresse):
    code, corps = lire(adresse + "/api/chemin", {"jeu": "petit", "source": "C1", "cible": "Q1", "algo": "bellman_ford"})
    assert code == 200
    assert json.loads(corps)["itineraire"]["duree"] == 4.0

    code, corps = lire(adresse + "/api/connexite", {"jeu": "petit", "routes_fermees": [["C1", "Q1"]]})
    assert code == 200
    assert json.loads(corps)["non_atteignables"] == []

    code, corps = lire(adresse + "/api/chemin", {"jeu": "petit", "source": "Z9"})
    assert code == 400


def test_serveur_page_routes_de_b(adresse):
    code, corps = lire(adresse + "/routes")

    assert code == 200
    assert "Salle de crise Novapolis" in corps.decode("utf-8")
