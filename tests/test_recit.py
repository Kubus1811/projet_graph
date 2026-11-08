import json

import pytest
from src.arbres import kruskal, kruskal_etapes, reparer_pannes
from src.graphe import Graphe
from src.recit import construire_recit
from src.salle_de_crise import _charger, points_faibles, simuler


@pytest.fixture(scope="module")
def recit():
    return construire_recit("realiste")


def par_id(recit):
    return {c["id"]: c for c in recit["chapitres"]}


def retard_total(etat):
    res = simuler("realiste", etat["routes_fermees"], etat["fibres_en_panne"], pointe=etat["pointe"])
    return sum(d["retard"] or 0 for d in res["demandes"])


def test_kruskal_etapes_retrouve_le_meme_arbre():
    g = _charger("realiste")["fibre"]
    gardees = [(e["u"], e["v"], e["cout"]) for e in kruskal_etapes(g) if e["gardee"]]

    assert gardees == kruskal(g)["aretes"]
    assert len(kruskal_etapes(g)) == len(g.arcs())


def test_kruskal_etapes_rejette_l_arete_qui_ferme_un_cycle():
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 1.0)
    g.ajouter_arc("B", "C", 2.0)
    g.ajouter_arc("A", "C", 3.0)

    assert [e["gardee"] for e in kruskal_etapes(g)] == [True, True, False]


def test_kruskal_etapes_refuse_un_graphe_oriente():
    with pytest.raises(ValueError):
        kruskal_etapes(Graphe(oriente=True))


def test_histoire_serialisable_sans_infini(recit):
    json.dumps(recit, allow_nan=False)


def test_histoire_dans_l_ordre_et_finit_a_l_aube(recit):
    ids = [c["id"] for c in recit["chapitres"]]

    assert ids == ["ronde", "soir", "pointe", "orage", "deblaiement", "reseau", "foudre", "isole", "aube"]


def test_tous_les_etats_de_l_histoire_se_simulent(recit):
    for c in recit["chapitres"]:
        e = c["etat"]
        simuler("realiste", e["routes_fermees"], e["fibres_en_panne"], pointe=e["pointe"])


def test_chapitre_normal_annonce_le_vrai_dernier_arrive(recit):
    dernier = max(d["temps_apres"] for d in simuler("realiste")["demandes"])
    texte = " ".join(par_id(recit)["soir"]["lignes"])

    assert f"{dernier:.1f}".replace(".", ",") in texte


def test_orage_frappe_les_routes_vraiment_critiques(recit):
    axes = points_faibles("realiste", limite=3)["routes"]

    assert par_id(recit)["orage"]["surlignes"] == [[a["u"], a["v"]] for a in axes]


def test_decision_deblaiement_marque_le_vrai_optimum(recit):
    options = par_id(recit)["deblaiement"]["decision"]["options"]
    valeurs = {o["id"]: retard_total(o["etat"]) for o in options}
    meilleurs = [o for o in options if o["meilleure"]]

    assert len(meilleurs) == 1
    assert valeurs[meilleurs[0]["id"]] == min(valeurs.values())
    for o in options:
        assert o["valeur"] == pytest.approx(valeurs[o["id"]])
        assert o["ecart"] == pytest.approx(valeurs[o["id"]] - min(valeurs.values()))


def test_decision_deblaiement_rouvre_bien_la_route_choisie(recit):
    for o in par_id(recit)["deblaiement"]["decision"]["options"]:
        a, b = o["surligne"]
        fermes = [tuple(f) for f in o["etat"]["routes_fermees"]]
        assert (a, b) not in fermes and (b, a) not in fermes
        assert fermes


def test_decision_fibre_optimum_egal_a_la_reparation_du_programme(recit):
    foudre = par_id(recit)["foudre"]
    panne = foudre["etat"]["fibres_en_panne"]
    attendu = reparer_pannes(_charger("realiste")["fibre"], panne)
    meilleure = next(o for o in foudre["decision"]["options"] if o["meilleure"])

    assert meilleure["valeur"] == attendu["cout_reparation"]
    assert len(foudre["decision"]["options"]) >= 2
    assert all(o["valeur"] >= meilleure["valeur"] for o in foudre["decision"]["options"])


def test_chapitre_isole_sur_un_troncon_vraiment_sans_secours(recit):
    panne = par_id(recit)["isole"]["etat"]["fibres_en_panne"]

    assert reparer_pannes(_charger("realiste")["fibre"], panne)["raccordements"] == []


def test_les_options_ne_trient_pas_la_bonne_reponse_en_premier(recit):
    for c in recit["chapitres"]:
        if c["decision"]:
            ids = [o["id"] for o in c["decision"]["options"]]
            assert ids == sorted(ids)


def test_histoire_annonce_que_les_donnees_sont_synthetiques(recit):
    assert "synthétiques" in recit["avertissement"]


def test_histoire_fonctionne_aussi_sur_le_petit_graphe():
    res = construire_recit("petit")

    json.dumps(res, allow_nan=False)
    assert res["chapitres"][0]["id"] == "ronde"
    assert res["chapitres"][-1]["id"] == "aube"


def test_construire_l_histoire_ne_modifie_pas_le_jeu():
    jeu = _charger("realiste")
    avant = (jeu["routes"].arcs(), jeu["fibre"].arcs())

    construire_recit("realiste")

    assert (jeu["routes"].arcs(), jeu["fibre"].arcs()) == avant


def test_ronde_reprend_le_diagnostic_de_b(recit):
    from src.parcours import diagnostic_accessibilite

    jeu = _charger("realiste")
    diag = diagnostic_accessibilite(jeu["routes"], jeu["casernes"])
    texte = " ".join(par_id(recit)["ronde"]["lignes"])

    assert f"{diag['nb_atteignables']} lieux sur {diag['nb_sites']}" in texte
    assert "une seule composante fortement connexe" in texte
    assert "0 écart" in texte
    assert par_id(recit)["ronde"]["vehicules"] is False
