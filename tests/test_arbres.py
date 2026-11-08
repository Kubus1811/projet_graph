import itertools
import random
from pathlib import Path

import pytest
from src.arbres import (
    UnionFind,
    analyser_panne,
    comparer_kruskal_prim,
    formater_comparaison_acm,
    formater_panne,
    kruskal,
    prim,
    trouver_composantes,
)
from src.cli import main
from src.graphe import Graphe
from src.indicateurs import evaluer_resilience_fibre
from src.io_donnees import charger_jeu_donnees

DOSSIER_DATA = Path(__file__).resolve().parent.parent / "data"


def graphe_fibre(aretes, sommets=()):
    g = Graphe(oriente=False)
    for s in sommets:
        g.ajouter_sommet(s)
    for u, v, cout in aretes:
        g.ajouter_arc(u, v, cout)
    return g


def test_union_find_etat_initial():
    uf = UnionFind(["A", "B", "C"])

    assert uf.nombre_ensembles == 3
    assert uf.trouver("A") == "A"
    assert uf.meme_ensemble("A", "B") is False


def test_union_find_vide():
    uf = UnionFind()

    assert uf.nombre_ensembles == 0


def test_union_find_ajouter_deux_fois_ne_change_rien():
    uf = UnionFind(["A", "B"])
    uf.unir("A", "B")
    uf.ajouter("A")

    assert uf.nombre_ensembles == 1
    assert uf.meme_ensemble("A", "B") is True


def test_union_find_unir_et_transitivite():
    uf = UnionFind(["A", "B", "C", "D"])

    assert uf.unir("A", "B") is True
    assert uf.unir("B", "C") is True
    assert uf.meme_ensemble("A", "C") is True
    assert uf.meme_ensemble("A", "D") is False
    assert uf.nombre_ensembles == 2


def test_union_find_detecte_un_cycle():
    uf = UnionFind(["A", "B", "C"])
    uf.unir("A", "B")
    uf.unir("B", "C")

    # A et C sont deja relies : le compteur ne doit pas bouger
    assert uf.unir("A", "C") is False
    assert uf.unir("A", "A") is False
    assert uf.nombre_ensembles == 1


def test_union_find_element_inconnu():
    uf = UnionFind(["A"])

    with pytest.raises(KeyError):
        uf.trouver("Z")


def test_union_find_compression_de_chemin():
    uf = UnionFind(["A", "B", "C", "D"])
    # chaine A -> B -> C -> D construite a la main
    uf._parent.update({"A": "B", "B": "C", "C": "D"})

    assert uf.trouver("A") == "D"
    assert uf._parent["A"] == "D"
    assert uf._parent["B"] == "D"
    assert uf._parent["C"] == "D"


def test_union_find_union_par_rang():
    uf = UnionFind(["A", "B", "C"])
    uf.unir("A", "B")
    grande_racine = uf.trouver("A")

    # C est seul : c'est lui qui passe sous l'arbre le plus haut
    uf.unir("C", "A")

    assert uf.trouver("C") == grande_racine
    assert uf._rang[grande_racine] == 1


def test_union_find_chaine_tres_longue_sans_recursion():
    n = 100000
    uf = UnionFind(range(n))
    # pire cas pour trouver : une chaine bien plus longue que la limite de recursion
    uf._parent.update({i: i + 1 for i in range(n - 1)})

    assert uf.trouver(0) == n - 1


def test_kruskal_petit_graphe_resultat_a_la_main():
    g = charger_jeu_donnees(DOSSIER_DATA / "petit")["graphe_fibre"]

    res = kruskal(g)

    # voir data/petit/resultats_attendus.md
    assert res["cout_total"] == 35.0
    assert res["nb_composantes"] == 1
    assert res["aretes"] == [
        ("Q3", "Q4", 3.0),
        ("C1", "E1", 4.0),
        ("E1", "Q2", 4.0),
        ("C1", "Q1", 5.0),
        ("C2", "Q4", 5.0),
        ("H1", "Q1", 6.0),
        ("Q2", "Q3", 8.0),
    ]


def test_kruskal_graphe_vide():
    res = kruskal(Graphe(oriente=False))

    assert res == {"aretes": [], "cout_total": 0.0, "nb_composantes": 0}


def test_kruskal_sommet_isole():
    res = kruskal(graphe_fibre([("A", "B", 2.0)], sommets=["Z"]))

    assert res["aretes"] == [("A", "B", 2.0)]
    assert res["nb_composantes"] == 2


def test_kruskal_foret_si_non_connexe():
    res = kruskal(graphe_fibre([("A", "B", 1.0), ("C", "D", 2.0), ("D", "E", 3.0)]))

    assert res["cout_total"] == 6.0
    assert res["nb_composantes"] == 2
    assert len(res["aretes"]) == 3


def test_kruskal_ignore_les_boucles():
    res = kruskal(graphe_fibre([("A", "A", 1.0), ("A", "B", 5.0)]))

    assert res["aretes"] == [("A", "B", 5.0)]


def test_kruskal_egalites_independantes_de_l_ordre_du_fichier():
    aretes = [("A", "B", 1.0), ("B", "C", 1.0), ("A", "C", 1.0)]

    res_1 = kruskal(graphe_fibre(aretes))
    res_2 = kruskal(graphe_fibre([(v, u, c) for u, v, c in reversed(aretes)]))

    assert res_1["aretes"] == [("A", "B", 1.0), ("A", "C", 1.0)]
    assert res_1 == res_2


def test_kruskal_refuse_un_graphe_oriente():
    with pytest.raises(ValueError):
        kruskal(Graphe(oriente=True))


def test_kruskal_ne_modifie_pas_le_graphe():
    g = graphe_fibre([("A", "B", 1.0), ("B", "C", 2.0), ("A", "C", 3.0)])
    avant = g.arcs()

    kruskal(g)

    assert g.arcs() == avant


def test_kruskal_meme_cout_que_la_force_brute():
    # sur de petits graphes on peut essayer tous les arbres possibles
    rng = random.Random(2026)
    for _ in range(30):
        sommets = list("ABCDEF")
        aretes = [(u, v, float(rng.randint(1, 6)))
                  for u, v in itertools.combinations(sommets, 2) if rng.random() < 0.7]
        res = kruskal(graphe_fibre(aretes, sommets=sommets))

        nb_aretes = len(sommets) - res["nb_composantes"]
        meilleur = float("inf")
        for choix in itertools.combinations(aretes, nb_aretes):
            uf = UnionFind(sommets)
            if all(uf.unir(u, v) for u, v, _ in choix):
                meilleur = min(meilleur, sum(c for _, _, c in choix))

        assert res["cout_total"] == meilleur


@pytest.mark.parametrize("jeu", ["realiste", "genere"])
def test_kruskal_nombre_d_aretes_sur_les_gros_jeux(jeu):
    g = charger_jeu_donnees(DOSSIER_DATA / jeu)["graphe_fibre"]

    res = kruskal(g)

    # propriete d'une foret couvrante : |E| = |V| - nombre de composantes
    assert len(res["aretes"]) == g.nombre_sommets() - res["nb_composantes"]


def test_prim_petit_graphe_resultat_a_la_main():
    g = charger_jeu_donnees(DOSSIER_DATA / "petit")["graphe_fibre"]

    res = prim(g)

    assert res["cout_total"] == 35.0
    assert res["nb_composantes"] == 1
    assert len(res["aretes"]) == 7


def test_prim_graphe_vide():
    res = prim(Graphe(oriente=False))

    assert res == {"aretes": [], "cout_total": 0.0, "nb_composantes": 0}


def test_prim_sommet_isole():
    res = prim(graphe_fibre([("A", "B", 2.0)], sommets=["Z"]))

    assert res["aretes"] == [("A", "B", 2.0)]
    assert res["nb_composantes"] == 2


def test_prim_foret_si_non_connexe():
    res = prim(graphe_fibre([("A", "B", 1.0), ("C", "D", 2.0), ("D", "E", 3.0)]))

    assert res["aretes"] == [("A", "B", 1.0), ("C", "D", 2.0), ("D", "E", 3.0)]
    assert res["cout_total"] == 6.0
    assert res["nb_composantes"] == 2


def test_prim_ignore_les_boucles():
    res = prim(graphe_fibre([("A", "A", 1.0), ("A", "B", 5.0)]))

    assert res["aretes"] == [("A", "B", 5.0)]


def test_prim_prend_l_arete_la_moins_chere_vers_un_sommet():
    # C est d'abord vu a 10 depuis A, puis a 1 depuis B : l'entree a 10 est perimee
    res = prim(graphe_fibre([("A", "C", 10.0), ("A", "B", 2.0), ("B", "C", 1.0)]))

    assert res["aretes"] == [("A", "B", 2.0), ("B", "C", 1.0)]
    assert res["cout_total"] == 3.0


def test_prim_egalites_independantes_de_l_ordre_du_fichier():
    aretes = [("A", "B", 1.0), ("B", "C", 1.0), ("A", "C", 1.0), ("C", "D", 1.0)]

    res_1 = prim(graphe_fibre(aretes))
    res_2 = prim(graphe_fibre([(v, u, c) for u, v, c in reversed(aretes)]))

    assert res_1 == res_2


def test_prim_refuse_un_graphe_oriente():
    with pytest.raises(ValueError):
        prim(Graphe(oriente=True))


def test_prim_ne_modifie_pas_le_graphe():
    g = graphe_fibre([("A", "B", 1.0), ("B", "C", 2.0), ("A", "C", 3.0)])
    avant = g.arcs()

    prim(g)

    assert g.arcs() == avant


def test_prim_meme_cout_que_kruskal_sur_graphes_aleatoires():
    rng = random.Random(2026)
    for _ in range(50):
        sommets = [f"S{i}" for i in range(rng.randint(2, 30))]
        aretes = [(u, v, float(rng.randint(1, 6)))
                  for u, v in itertools.combinations(sommets, 2) if rng.random() < 0.15]
        g = graphe_fibre(aretes, sommets=sommets)

        res_k = kruskal(g)
        res_p = prim(g)

        assert res_p["cout_total"] == res_k["cout_total"]
        assert res_p["nb_composantes"] == res_k["nb_composantes"]


@pytest.mark.parametrize("jeu", ["petit", "realiste", "genere"])
def test_prim_forme_une_foret_de_meme_cout_que_kruskal(jeu):
    g = charger_jeu_donnees(DOSSIER_DATA / jeu)["graphe_fibre"]

    res_p = prim(g)
    res_k = kruskal(g)

    # les aretes existent et aucune ne ferme de cycle
    uf = UnionFind(g.sommets())
    for u, v, cout in res_p["aretes"]:
        assert g.poids_arc(u, v) == cout
        assert uf.unir(u, v) is True

    assert len(res_p["aretes"]) == g.nombre_sommets() - res_p["nb_composantes"]
    # sommes faites dans un ordre different : ecart d'arrondi possible sur les flottants
    assert res_p["cout_total"] == pytest.approx(res_k["cout_total"])


def test_composantes_graphe_vide():
    assert trouver_composantes(Graphe(oriente=False)) == []


def test_composantes_graphe_connexe():
    g = graphe_fibre([("A", "B", 1.0), ("B", "C", 1.0)])

    assert trouver_composantes(g) == [["A", "B", "C"]]


def test_composantes_la_plus_grande_d_abord_et_sommet_isole():
    g = graphe_fibre([("X", "Y", 1.0), ("B", "C", 1.0), ("C", "D", 1.0)], sommets=["Z"])

    assert trouver_composantes(g) == [["B", "C", "D"], ["X", "Y"], ["Z"]]


def test_composantes_refuse_un_graphe_oriente():
    with pytest.raises(ValueError):
        trouver_composantes(Graphe(oriente=True))


def test_composantes_coherentes_avec_kruskal_et_prim():
    rng = random.Random(2026)
    for _ in range(30):
        sommets = [f"S{i}" for i in range(rng.randint(1, 25))]
        aretes = [(u, v, 1.0) for u, v in itertools.combinations(sommets, 2) if rng.random() < 0.08]
        g = graphe_fibre(aretes, sommets=sommets)

        nb = len(trouver_composantes(g))

        assert nb == kruskal(g)["nb_composantes"]
        assert nb == prim(g)["nb_composantes"]


def test_composantes_utilisees_par_le_module_5():
    g = graphe_fibre([("A", "B", 1.0)], sommets=["Z"])

    res = evaluer_resilience_fibre(g)

    assert res == {"nb_composantes": 2, "est_connexe": False}


def test_comparaison_meme_arbre():
    g = charger_jeu_donnees(DOSSIER_DATA / "petit")["graphe_fibre"]

    comp = comparer_kruskal_prim(g)

    assert comp["meme_cout"] is True
    assert comp["meme_arbre"] is True
    assert comp["seulement_kruskal"] == []
    assert comp["seulement_prim"] == []


def test_egalites_kruskal_et_prim_donnent_deux_arbres_de_meme_cout():
    g = charger_jeu_donnees(DOSSIER_DATA / "egalites")["graphe_fibre"]

    comp = comparer_kruskal_prim(g)

    assert comp["kruskal"]["cout_total"] == 5.0
    assert comp["prim"]["cout_total"] == 5.0
    assert comp["meme_arbre"] is False
    assert comp["seulement_kruskal"] == [("B", "D", 2.0)]
    assert comp["seulement_prim"] == [("C", "E", 2.0)]


def test_egalites_exactement_deux_arbres_minimaux():
    g = charger_jeu_donnees(DOSSIER_DATA / "egalites")["graphe_fibre"]
    aretes = g.arcs()

    arbres_par_cout = {}
    for choix in itertools.combinations(aretes, g.nombre_sommets() - 1):
        uf = UnionFind(g.sommets())
        if all(uf.unir(u, v) for u, v, _ in choix):
            cout = sum(c for _, _, c in choix)
            arbres_par_cout[cout] = arbres_par_cout.get(cout, 0) + 1

    assert arbres_par_cout == {5.0: 2, 6.0: 3}


def test_poids_distincts_un_seul_arbre_minimal():
    # si tous les couts sont differents l'arbre minimal est unique
    rng = random.Random(2026)
    for _ in range(50):
        sommets = [f"S{i}" for i in range(rng.randint(2, 25))]
        paires = [p for p in itertools.combinations(sommets, 2) if rng.random() < 0.3]
        couts = rng.sample(range(1, 1000), len(paires))
        aretes = [(u, v, float(c)) for (u, v), c in zip(paires, couts)]

        comp = comparer_kruskal_prim(graphe_fibre(aretes, sommets=sommets))

        assert comp["meme_arbre"] is True


def test_cli_affiche_les_troncons_differents(capsys):
    code = main(["--donnees", str(DOSSIER_DATA / "egalites"), "--operation", "mst"])

    sortie = capsys.readouterr().out
    assert code == 0
    assert "Meme arbre : non (1 troncon(s) different(s))" in sortie
    assert "seulement Kruskal : B - D (2.00)" in sortie
    assert "seulement Prim    : C - E (2.00)" in sortie


def test_sortie_lisible_graphe_connexe():
    g = charger_jeu_donnees(DOSSIER_DATA / "petit")["graphe_fibre"]

    texte = formater_comparaison_acm(g)

    assert "Kruskal : 7 troncons, cout total 35.00, 1 composante(s)" in texte
    assert "Prim    : 7 troncons, cout total 35.00, 1 composante(s)" in texte
    assert "Meme cout total : oui" in texte
    assert "Q3 - Q4 : 3.00" in texte
    assert "Composantes non raccordees : aucune" in texte


def test_sortie_lisible_liste_les_parties_non_raccordees():
    g = graphe_fibre([("A", "B", 1.0), ("B", "C", 2.0), ("X", "Y", 3.0)], sommets=["Z"])

    texte = formater_comparaison_acm(g)

    assert "Composantes non raccordees : 2" in texte
    assert "['X', 'Y']" in texte
    assert "['Z']" in texte


def test_cli_operation_mst(capsys):
    code = main(["--donnees", str(DOSSIER_DATA / "petit"), "--operation", "mst"])

    assert code == 0
    assert "cout total 35.00" in capsys.readouterr().out


def test_panne_petit_graphe_resultat_a_la_main():
    g = charger_jeu_donnees(DOSSIER_DATA / "petit")["graphe_fibre"]

    res = analyser_panne(g, "Q2", "Q3")

    # voir data/petit/resultats_attendus.md
    assert res["dans_arbre"] is True
    assert res["nb_composantes_panne"] == 2
    assert res["cote_1"] == ["C1", "E1", "H1", "Q1", "Q2"]
    assert res["cote_2"] == ["C2", "Q3", "Q4"]
    assert res["raccordement"] == ("C2", "E1", 9.0)
    assert res["cout_reparation"] == 9.0
    assert res["cout_arbre_avant"] == 35.0
    assert res["cout_arbre_apres"] == 36.0


def test_panne_extremites_dans_les_deux_sens():
    g = charger_jeu_donnees(DOSSIER_DATA / "petit")["graphe_fibre"]

    assert analyser_panne(g, "Q3", "Q2") == analyser_panne(g, "Q2", "Q3")


def test_panne_troncon_hors_de_l_arbre():
    g = charger_jeu_donnees(DOSSIER_DATA / "petit")["graphe_fibre"]

    res = analyser_panne(g, "Q1", "Q2")

    assert res["dans_arbre"] is False
    assert res["raccordable"] is True
    assert res["raccordement"] is None
    assert res["cout_reparation"] == 0.0
    assert res["cout_arbre_apres"] == 35.0
    assert res["nb_composantes_panne"] == 1


def test_panne_d_un_pont_sans_raccordement_possible():
    g = graphe_fibre([("A", "B", 1.0), ("B", "C", 2.0)])

    res = analyser_panne(g, "B", "C")

    assert res["raccordable"] is False
    assert res["raccordement"] is None
    assert res["cout_reparation"] == 0.0
    assert res["cout_arbre_apres"] == 1.0
    assert res["nb_composantes_panne"] == 2


def test_panne_seul_raccordement_indisponible():
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 1.0)
    g.ajouter_arc("B", "D", 2.0)
    g.ajouter_arc("A", "D", 3.0, statut="travaux")

    # D ne peut etre reconnecte que par A-D, en travaux
    res = analyser_panne(g, "B", "D")

    assert res["dans_arbre"] is True
    assert res["raccordable"] is False


def test_panne_prefere_un_troncon_ouvert_plus_cher():
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 1.0)
    g.ajouter_arc("B", "C", 1.0)
    g.ajouter_arc("B", "D", 2.0)
    g.ajouter_arc("A", "D", 3.0, statut="ferme")
    g.ajouter_arc("C", "D", 4.0, statut="ouvert")

    res = analyser_panne(g, "B", "D")

    assert res["raccordement"] == ("C", "D", 4.0)
    assert res["cout_reparation"] == 4.0


def test_panne_troncon_inexistant():
    g = graphe_fibre([("A", "B", 1.0)], sommets=["Z"])

    with pytest.raises(ValueError):
        analyser_panne(g, "A", "Z")


def test_panne_refuse_un_graphe_oriente():
    with pytest.raises(ValueError):
        analyser_panne(Graphe(oriente=True), "A", "B")


def test_panne_ne_modifie_pas_le_graphe():
    g = charger_jeu_donnees(DOSSIER_DATA / "petit")["graphe_fibre"]
    avant = g.arcs()

    analyser_panne(g, "Q2", "Q3")

    assert g.arcs() == avant
    assert g.a_arc("Q2", "Q3") is True


def test_panne_meme_cout_que_kruskal_relance_sans_le_troncon():
    # reparer avec l'arete la moins chere redonne un arbre minimal du graphe sans la panne
    rng = random.Random(2026)
    for _ in range(30):
        sommets = [f"S{i}" for i in range(rng.randint(2, 20))]
        aretes = [(u, v, float(rng.randint(1, 9)))
                  for u, v in itertools.combinations(sommets, 2) if rng.random() < 0.25]
        g = graphe_fibre(aretes, sommets=sommets)

        for u, v, _ in kruskal(g)["aretes"]:
            res = analyser_panne(g, u, v)
            g_sans = g.copie()
            g_sans.supprimer_arc(u, v)
            attendu = kruskal(g_sans)

            assert res["cout_arbre_apres"] == attendu["cout_total"]
            assert res["raccordable"] == (attendu["nb_composantes"] == kruskal(g)["nb_composantes"])


def test_sortie_lisible_panne():
    g = charger_jeu_donnees(DOSSIER_DATA / "petit")["graphe_fibre"]

    texte = formater_panne(analyser_panne(g, "Q2", "Q3"))

    assert "Panne du troncon Q2 - Q3 (cout 8.00)" in texte
    assert "Raccordement le moins cher : C2 - E1 (cout 9.00)" in texte
    assert "Cout de l'arbre : 35.00 -> 36.00" in texte


def test_sortie_lisible_panne_sans_raccordement():
    g = graphe_fibre([("A", "B", 1.0)])

    assert "Raccordement impossible" in formater_panne(analyser_panne(g, "A", "B"))


def test_cli_operation_panne(capsys):
    code = main(["--donnees", str(DOSSIER_DATA / "petit"), "--operation", "panne"])

    sortie = capsys.readouterr().out
    assert code == 0
    assert "panne_fibre_troncon_central" in sortie
    assert "C2 - E1 (cout 9.00)" in sortie


def test_cli_panne_scenario_inconnu(capsys):
    code = main(["--donnees", str(DOSSIER_DATA / "petit"), "--scenario", "inconnu", "--operation", "panne"])

    assert code == 1
    assert "Aucune panne" in capsys.readouterr().out


def test_cli_panne_sans_scenario_dans_le_jeu(capsys):
    code = main(["--donnees", str(DOSSIER_DATA / "egalites"), "--operation", "panne"])

    assert code == 1
    assert "Aucune panne" in capsys.readouterr().out


def graphe_avec_troncon(statut):
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 1.0, statut=statut)
    g.ajouter_arc("B", "C", 2.0, statut="ouvert")
    g.ajouter_arc("A", "C", 5.0, statut="ouvert")
    return g


@pytest.mark.parametrize("statut", ["ferme", "travaux"])
def test_kruskal_et_prim_ignorent_un_troncon_indisponible(statut):
    # A-B est le moins cher mais ne peut pas porter la fibre : il faut passer par A-C
    g = graphe_avec_troncon(statut)

    for algo in (kruskal, prim):
        res = algo(g)
        assert sorted(res["aretes"]) == [("A", "C", 5.0), ("B", "C", 2.0)]
        assert res["cout_total"] == 7.0


def test_troncon_indisponible_ne_relie_pas_deux_composantes():
    g = Graphe(oriente=False)
    g.ajouter_arc("A", "B", 1.0)
    g.ajouter_arc("B", "C", 2.0, statut="ferme")

    assert trouver_composantes(g) == [["A", "B"], ["C"]]
    assert kruskal(g)["nb_composantes"] == 2
    assert prim(g)["nb_composantes"] == 2


def test_panne_le_troncon_indisponible_n_est_pas_dans_l_arbre():
    g = graphe_avec_troncon("ferme")

    res = analyser_panne(g, "A", "B")

    assert res["dans_arbre"] is False
    assert res["cout_arbre_avant"] == 7.0
