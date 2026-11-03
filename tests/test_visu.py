import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame = pytest.importorskip("pygame")
from pygame.math import Vector2

from src.io_donnees import charger_jeu_donnees
from src.visu import (
    Visualiseur, projeter_sites, geometrie_fleche, point_sur_polyligne,
    longueur_polyligne, position_poids, texte_poids, capturer, COUL_CHEMIN, COUL_FERME, PANNEAU, main,
)


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def petit():
    return charger_jeu_donnees("data/petit")


# ---------------------------------------------------------------- vecteurs


def test_projection_dans_la_fenetre(petit):
    pos = projeter_sites(petit["sites"], 900, 800, marge=40)
    for p in pos.values():
        assert 40 - 1e-6 <= p.x <= 860 + 1e-6
        assert 40 - 1e-6 <= p.y <= 760 + 1e-6
    # le nord est en haut : H1 (lat 48.88) au-dessus de C2 (lat 48.82)
    assert pos["H1"].y < pos["C2"].y
    # l'est est a droite
    assert pos["Q3"].x > pos["C1"].x


def test_fleche_raccourcie_et_decalee():
    a, b = Vector2(0, 0), Vector2(100, 0)
    debut, fin, triangle = geometrie_fleche(a, b, rayon=10, decalage=3, taille=8)
    assert debut == Vector2(10, 3)
    assert fin == Vector2(90, 3)
    # la pointe du triangle est sur la fin, la base 8 px en arriere
    assert triangle[0] == fin
    assert triangle[1].x == pytest.approx(82) and triangle[2].x == pytest.approx(82)
    # u->v et v->u sont decales de part et d'autre
    debut_retour, _, _ = geometrie_fleche(b, a, rayon=10, decalage=3)
    assert debut_retour.y == pytest.approx(-3)


def test_fleche_trop_courte():
    assert geometrie_fleche(Vector2(0, 0), Vector2(5, 0), rayon=10) is None


def test_point_sur_polyligne():
    pts = [Vector2(0, 0), Vector2(10, 0), Vector2(10, 10)]
    assert longueur_polyligne(pts) == 20
    assert point_sur_polyligne(pts, 5) == Vector2(5, 0)
    assert point_sur_polyligne(pts, 15) == Vector2(10, 5)
    assert point_sur_polyligne(pts, 99) == Vector2(10, 10)


# ---------------------------------------------------------------- visualiseur


def test_chemin_et_scenario(petit):
    vis = Visualiseur(petit)
    vis.source, vis.cible = "C1", "Q1"
    vis.recalculer()
    assert vis.itineraire["chemin"] == ["C1", "Q1"]

    vis.changer_scenario(vis.scenarios.index("fermeture_route_C1_Q1"))
    assert vis.itineraire["chemin"] == ["C1", "E1", "Q2", "Q1"]
    assert vis.itineraire["duree"] == 10 and vis.duree_ref == 4
    # le graphe de reference n'est pas touche
    assert vis.g_ref.a_arc("C1", "Q1")


@pytest.mark.parametrize("algo", ["dijkstra", "bellman_ford", "floyd_warshall"])
def test_meme_chemin_pour_les_3_algos(petit, algo):
    vis = Visualiseur(petit)
    vis.algo = algo
    vis.source, vis.cible = "C2", "H1"
    vis.recalculer()
    assert vis.itineraire["chemin"] == ["C2", "Q4", "Q3", "H1"]


def test_clic_selectionne_le_sommet(petit):
    vis = Visualiseur(petit)
    p = vis.ecran("E1")
    vis.gerer_evenement(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(int(p.x), int(p.y))))
    assert vis.source == "E1"


def test_zoom_garde_le_point_sous_la_souris(petit):
    vis = Visualiseur(petit)
    p = vis.ecran("Q2")
    vis.zoomer(2.0, p)
    assert vis.ecran("Q2").distance_to(p) < 1e-6


def test_rendu_chemin_et_route_fermee(petit, tmp_path):
    vis = Visualiseur(petit)
    vis.source, vis.cible = "C1", "Q1"
    vis.changer_scenario(vis.scenarios.index("fermeture_route_C1_Q1"))
    surf = capturer(vis, tmp_path / "visu.png")
    assert (tmp_path / "visu.png").exists()

    couleurs = {tuple(surf.get_at((x, y)))[:3]
                for x in range(0, surf.get_width() - PANNEAU, 2)
                for y in range(0, surf.get_height(), 2)}
    assert COUL_CHEMIN in couleurs
    assert COUL_FERME in couleurs


@pytest.mark.parametrize("mode", ["accessibilite", "cfc", "itineraires"])
def test_modes_rendus(petit, tmp_path, mode):
    vis = Visualiseur(petit)
    vis.changer_mode(mode)
    capturer(vis, tmp_path / f"{mode}.png")
    assert (tmp_path / f"{mode}.png").exists()


def test_cli_capture_realiste(tmp_path):
    sortie = tmp_path / "realiste.png"
    code = main(["--donnees", "data/realiste", "--source", "CAS_01", "--cible", "QUA_007",
                 "--scenario", "heure_pointe_generale", "--capture", str(sortie)])
    pygame.init()  # main() appelle pygame.quit()
    assert code == 0 and sortie.exists()


# ---------------------------------------------------------------- poids des arcs


def test_position_poids_de_part_et_d_autre():
    a, b = Vector2(0, 0), Vector2(100, 0)
    aller = position_poids(a, b, ecart=10)
    retour = position_poids(b, a, ecart=10)
    assert aller.x == pytest.approx(50) and retour.x == pytest.approx(50)
    # u->v et v->u sont de chaque cote de la route, sans se chevaucher
    assert aller.y == pytest.approx(10) and retour.y == pytest.approx(-10)


def test_texte_poids():
    assert texte_poids(4.0) == "4"
    assert texte_poids(3.9) == "3.9"


def test_touche_w_affiche_les_poids(petit, tmp_path):
    vis = Visualiseur(petit)
    assert not vis.afficher_poids
    vis.gerer_evenement(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w))
    assert vis.afficher_poids
    capturer(vis, tmp_path / "poids.png")
    # sur le petit jeu les arcs sont assez longs : aucun poids n'est cache
    assert vis.poids_caches == 0


def test_panneau_detaille_la_somme(petit):
    vis = Visualiseur(petit)
    vis.source, vis.cible = "C1", "Q1"
    vis.changer_scenario(vis.scenarios.index("fermeture_route_C1_Q1"))
    textes = [txt for txt, _ in vis.lignes_panneau()]
    assert "= 5 + 2 + 3" in textes


def test_poids_suivent_le_scenario(petit):
    # en heure de pointe le poids affiche est le temps de pointe
    vis = Visualiseur(petit)
    vis.changer_scenario(vis.scenarios.index("heure_pointe_generale"))
    assert vis.g.poids_arc("C1", "Q1") == 8.0
    assert vis.g_ref.poids_arc("C1", "Q1") == 4.0
