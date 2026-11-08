from src.arbres import _aretes_triees, analyser_panne, kruskal, kruskal_etapes
from src.chemins import comparer_algorithmes
from src.parcours import diagnostic_accessibilite
from src.salle_de_crise import TAILLE_MAX_FLOYD, _charger, moteur_itineraires, points_faibles, simuler

# L'histoire est inventee mais aucun chiffre n'est ecrit a la main :
# chaque nombre affiche vient d'un calcul fait ici, sur les donnees du jeu.


def _min(x):
    return f"{x:.1f}".replace(".", ",") + " min"


def _k(x):
    return f"{x:.1f}".replace(".", ",") + " k€"


def _etat(routes_fermees=(), fibres_en_panne=(), pointe=False):
    return {
        "routes_fermees": [list(a) for a in routes_fermees],
        "fibres_en_panne": [list(a) for a in fibres_en_panne],
        "pointe": pointe,
    }


def _indicateurs(nom, etat):
    return simuler(nom, etat["routes_fermees"], etat["fibres_en_panne"], pointe=etat["pointe"])["indicateurs"]


def _retard_total(nom, etat):
    res = simuler(nom, etat["routes_fermees"], etat["fibres_en_panne"], pointe=etat["pointe"])
    return sum(d["retard"] or 0 for d in res["demandes"])


def _chapitre(identifiant, heure, titre, lignes, radio, algorithme, idee, etat, vue="routes",
              ambiance="nuit", decision=None, kruskal_visible=False, surlignes=(), vehicules=True):
    return {
        "id": identifiant,
        "heure": heure,
        "titre": titre,
        "lignes": lignes,
        "radio": radio,
        "algorithme": {"nom": algorithme, "idee": idee},
        "etat": etat,
        "vue": vue,
        "ambiance": ambiance,
        "decision": decision,
        "kruskal": kruskal_visible,
        "surlignes": [list(s) for s in surlignes],
        "vehicules": vehicules,
    }


def _decision_deblaiement(nom, axes):
    # chaque option : on rouvre un axe et les autres restent coupes
    options = []
    for choisi in axes:
        fermes = [f for a in axes if a is not choisi for f in a["routes_fermees"]]
        etat = _etat(fermes)
        i = _indicateurs(nom, etat)
        options.append({
            "id": f"{choisi['u']}|{choisi['v']}",
            "libelle": f"Dégager {choisi['u']} ↔ {choisi['v']}",
            "etat": etat,
            "surligne": [choisi["u"], choisi["v"]],
            "inaccessibles": i["inaccessibles"],
            "valeur": _retard_total(nom, etat),
        })

    meilleure = min(options, key=lambda o: (o["inaccessibles"], o["valeur"]))
    for o in options:
        o["meilleure"] = o is meilleure
        o["ecart"] = o["valeur"] - meilleure["valeur"]
        o["reponse"] = f"Retard cumulé restant : {_min(o['valeur'])}."

    return {
        "question": "Vous n'avez qu'une équipe de déblaiement. Quelle route dégagez-vous en premier ?",
        "unite": "min de retard cumulé",
        "options": sorted(options, key=lambda o: o["id"]),
        "explication": f"Le programme a recalculé tous les trajets pour chaque choix. Le meilleur laisse {_min(meilleure['valeur'])} de retard cumulé.",
    }


def _troncons_de_secours(fibre, u, v):
    panne = analyser_panne(fibre, u, v)
    cote_1, cote_2 = set(panne["cote_1"]), set(panne["cote_2"])
    cle = (panne["panne"][0], panne["panne"][1])
    return panne, [
        (a, b, cout) for cout, a, b in _aretes_triees(fibre)
        if (a, b) != cle and ((a in cote_1 and b in cote_2) or (a in cote_2 and b in cote_1))
    ]


def _decision_fibre(nom, jeu, impacts):
    # on prend le troncon le plus couteux a reparer qui laisse un vrai choix
    for impact in impacts:
        if not impact["raccordable"]:
            continue
        panne, secours = _troncons_de_secours(jeu["fibre"], impact["u"], impact["v"])
        if len(secours) < 2:
            continue

        retenus = secours[:3]
        moins_cher = retenus[0][2]
        avant, perdu = panne["cout_arbre_avant"], impact["cout"]
        options = [
            {
                "id": f"{a}|{b}",
                "libelle": f"Poser {a} – {b}",
                "surligne": [a, b],
                "valeur": cout,
                "meilleure": cout == moins_cher,
                "ecart": cout - moins_cher,
                "reponse": f"Le réseau repart pour {_k(cout)}. Son coût total passe à {_k(avant - perdu + cout)}.",
            }
            for a, b, cout in retenus
        ]
        return impact, {
            "question": "Le réseau est coupé en deux. Quel tronçon faites-vous poser ?",
            "unite": "k€",
            "options": sorted(options, key=lambda o: o["id"]),
            "explication": f"La propriété de coupure garantit que le tronçon le moins cher entre les deux côtés redonne un arbre minimal : {_k(moins_cher)} ici.",
        }
    return None, None


def construire_recit(nom="realiste"):
    jeu = _charger(nom)
    faibles = points_faibles(nom, limite=3)
    normal = simuler(nom)
    total = normal["indicateurs"]["total_demandes"]
    dernier = max(d["temps_apres"] for d in normal["demandes"] if d["accessible"])
    arbre = kruskal(jeu["fibre"])
    casernes = len(jeu["casernes"])
    chapitres = []

    # partie B, module 1 et verification B13 : la ronde avant la nuit
    diag = diagnostic_accessibilite(jeu["routes"], jeu["casernes"])
    avec_floyd = jeu["routes"].nombre_sommets() <= TAILLE_MAX_FLOYD
    ecarts = comparer_algorithmes(jeu["routes"], sources=jeu["casernes"], avec_floyd=avec_floyd)
    comparees = len(jeu["casernes"]) * diag["nb_sites"]
    algos = "Dijkstra, Bellman-Ford et Floyd-Warshall" if avec_floyd else "Dijkstra et Bellman-Ford"
    if diag["nb_cfc"] == 1:
        connexite = "Le réseau forme une seule composante fortement connexe : depuis n'importe quel lieu, on peut aller partout et revenir."
    else:
        connexite = f"Le réseau compte {diag['nb_cfc']} composantes fortement connexes : certains lieux sont atteignables, mais on ne peut pas en revenir."
    chapitres.append(_chapitre(
        "ronde", "21 h 00", "La ronde de contrôle",
        [
            f"Avant la prise de service, vous vérifiez le réseau routier. Depuis les {casernes} casernes, {diag['nb_atteignables']} lieux sur {diag['nb_sites']} sont atteignables, dont {diag['sensibles_accessibles']} sites sensibles sur {diag['sensibles_total']}.",
            connexite,
            f"{algos} donnent {'les mêmes' if not ecarts else 'des'} distances depuis chaque caserne : {comparees} distances comparées, {len(ecarts)} écart.",
        ],
        "Contrôle du réseau terminé. Tous les lieux sont accessibles." if not diag["non_atteignables"] else "Contrôle terminé. Attention, des lieux ne sont pas accessibles.",
        "BFS, Kosaraju et comparaison des 3 algorithmes",
        "Le BFS part de toutes les casernes à la fois. Accessible ne veut pas dire fortement connexe : il faut aussi pouvoir revenir.",
        _etat(), ambiance="soir", vehicules=False,
    ))

    chapitres.append(_chapitre(
        "soir", "21 h 40", "Une soirée ordinaire",
        [
            f"Vous prenez votre service de régulateur. Novapolis compte {len(jeu['sites'])} sites et {casernes} casernes.",
            f"{total} appels arrivent. Pour chacun, le programme cherche la caserne la plus proche et le trajet le plus rapide. Le dernier véhicule arrive au bout de {_min(dernier)}.",
        ],
        f"Ici la régulation. {total} interventions en cours. Tous les quartiers sont accessibles.",
        "Dijkstra",
        "Il part de la caserne et avance toujours vers le lieu le plus proche qu'il n'a pas encore fixé, comme un GPS.",
        _etat(), ambiance="soir",
    ))

    etat_pointe = _etat(pointe=True)
    i_pointe = _indicateurs(nom, etat_pointe)
    chapitres.append(_chapitre(
        "pointe", "22 h 30", "La sortie du stade",
        [
            "Le match se termine et la ville se remplit de voitures. Les routes existent toujours, mais elles sont plus lentes.",
            f"Le programme relance les calculs avec les temps de pointe : en moyenne {_min(i_pointe['retard_moyen'])} de plus par intervention, et jusqu'à {_min(i_pointe['retard_max'])} pour la plus touchée.",
        ],
        f"Circulation dense sur tout le réseau. Retard moyen de {round(i_pointe['retard_moyen'])} minutes.",
        "Dijkstra, sur les temps de pointe",
        "Même algorithme, autres poids. Le meilleur trajet n'est plus forcément le même.",
        etat_pointe, ambiance="pointe",
    ))

    axes = faibles["routes"]
    if len(axes) >= 2:
        fermes = [f for a in axes for f in a["routes_fermees"]]
        etat_orage = _etat(fermes)
        i_orage = _indicateurs(nom, etat_orage)
        noms = ", ".join(f"{a['u']} ↔ {a['v']}" for a in axes)
        chapitres.append(_chapitre(
            "orage", "23 h 15", "L'orage",
            [
                f"La tempête arrive. Des arbres tombent sur {noms}.",
                f"Ces routes ne sont pas choisies au hasard : ce sont les plus critiques parmi les {faibles['nb_axes_testes']} axes testés. Résultat : {i_orage['inaccessibles']} demande(s) sans secours et jusqu'à {_min(i_orage['retard_max'])} de retard.",
            ],
            "Alerte. Plusieurs axes sont coupés par des chutes d'arbres. Les véhicules sont déroutés.",
            "Test de résistance",
            "Le programme coupe chaque route une par une, relance les calculs et classe les dégâts.",
            etat_orage, ambiance="orage", surlignes=[(a["u"], a["v"]) for a in axes],
        ))
        chapitres.append(_chapitre(
            "deblaiement", "23 h 40", "Une seule équipe",
            ["Les pompiers n'ont qu'une équipe disponible pour dégager une route. Chaque minute compte, et c'est à vous de décider."],
            "Régulation, à vous de décider. Quelle route devons-nous dégager en premier ?",
            "Comparaison de scénarios",
            "Le programme calcule chaque choix sur une copie de la ville. Le réseau de référence ne change jamais.",
            etat_orage, ambiance="orage", decision=_decision_deblaiement(nom, axes),
            surlignes=[(a["u"], a["v"]) for a in axes],
        ))

    gardees = len(arbre["aretes"])
    chapitres.append(_chapitre(
        "reseau", "00 h 30", "Le réseau invisible",
        [
            "Pour coordonner les secours, la ville compte sur sa fibre optique. Voici comment elle a été conçue au moindre coût.",
            f"Kruskal prend les {len(jeu['fibre'].arcs())} tronçons possibles, du moins cher au plus cher, et ne rejette que ceux qui fermeraient une boucle. Il en garde {gardees}, pour {_k(arbre['cout_total'])}.",
        ],
        "Vérification du réseau de fibre en cours.",
        "Kruskal et Union-Find",
        "Si les deux bouts d'un tronçon sont déjà reliés, il ne sert à rien : on le rejette.",
        _etat(), vue="fibre", ambiance="nuit", kruskal_visible=True,
    ))

    impact, decision = _decision_fibre(nom, jeu, faibles["fibre_toutes"])
    if decision:
        chapitres.append(_chapitre(
            "foudre", "01 h 05", "La foudre",
            [
                f"La foudre frappe le tronçon {impact['u']} – {impact['v']}. Le réseau se coupe en deux morceaux.",
                "Plusieurs tronçons existants peuvent relier les deux côtés, à des prix différents.",
            ],
            f"Panne de fibre sur {impact['u']}, {impact['v']}. Le réseau est coupé en deux.",
            "Propriété de coupure",
            "Parmi les tronçons qui relient les deux côtés, le moins cher redonne un arbre minimal.",
            _etat(fibres_en_panne=[(impact["u"], impact["v"])]),
            vue="fibre", ambiance="foudre", decision=decision, surlignes=[(impact["u"], impact["v"])],
        ))

    sans_secours = [t for t in faibles["fibre_toutes"] if not t["raccordable"]]
    if sans_secours:
        t = sans_secours[0]
        panne = analyser_panne(jeu["fibre"], t["u"], t["v"])
        isoles = min(panne["cote_1"], panne["cote_2"], key=len)
        chapitres.append(_chapitre(
            "isole", "03 h 10", "Le quartier coupé",
            [
                f"Dernier coup dur : le tronçon {t['u']} – {t['v']} lâche. Cette fois, aucun autre tronçon ne relie les deux côtés.",
                f"{len(isoles)} site(s) restent coupés du réseau : {', '.join(isoles[:6])}{'…' if len(isoles) > 6 else ''}. Avec les données actuelles, aucun tronçon ne peut les raccorder.",
            ],
            "Liaison perdue. Aucun tronçon de secours n'est disponible pour ce secteur.",
            "Forêt couvrante",
            "Sans arête disponible entre deux morceaux, le meilleur résultat reste deux arbres séparés.",
            _etat(fibres_en_panne=[(t["u"], t["v"])]),
            vue="fibre", ambiance="foudre", surlignes=[(t["u"], t["v"])],
        ))

    recommandations = []
    if axes:
        a = axes[0]
        recommandations.append(f"Prévoir un itinéraire de secours autour de {a['u']} ↔ {a['v']} : sa fermeture coûte {_min(a['retard_total'])} de retard cumulé.")
    if sans_secours:
        liste = ", ".join(f"{t['u']} – {t['v']}" for t in sans_secours)
        recommandations.append(f"Étudier une liaison de secours pour {liste}, qui n'ont aujourd'hui aucun raccordement possible.")
    recommandations.append("Ne plus choisir les scénarios à la main : le test de résistance a trouvé des points faibles que les scénarios écrits ne révélaient pas.")

    chapitres.append(_chapitre(
        "aube", "06 h 00", "L'aube",
        [
            "L'orage s'éloigne et les routes sont rouvertes. Il est temps de faire le bilan de votre nuit.",
            "Limites à garder en tête : les données sont synthétiques, les temps de trajet sont fixes, et le modèle ignore la priorité des appels et le nombre de véhicules disponibles.",
        ],
        "Fin de l'alerte. Merci à toutes les équipes.",
        "Bilan",
        "Une décision se juge en la comparant à l'optimum, calculé sur les mêmes données.",
        _etat(), ambiance="aube",
    ))

    return {
        "jeu": nom,
        "titre": "La nuit de l'orage",
        "avertissement": "Histoire inventée, données synthétiques. Tous les chiffres sont calculés par le programme.",
        "chapitres": chapitres,
        "kruskal_etapes": kruskal_etapes(jeu["fibre"]),
        "recommandations": recommandations,
        "moteur": moteur_itineraires(),
    }
