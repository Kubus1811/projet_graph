import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src import recit, salle_de_crise

PAGE_RECIT = Path(__file__).resolve().parent / "recit.html"
PAGE_SALLE = Path(__file__).resolve().parent / "salle_de_crise.html"
TAILLE_MAX_REQUETE = 1_000_000


class Gestionnaire(BaseHTTPRequestHandler):
    def _repondre(self, code, contenu, type_contenu):
        self.send_response(code)
        self.send_header("Content-Type", type_contenu)
        self.send_header("Content-Length", str(len(contenu)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(contenu)

    def _repondre_json(self, code, donnees):
        # allow_nan=False : une distance infinie ne doit jamais partir dans le json
        contenu = json.dumps(donnees, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self._repondre(code, contenu, "application/json; charset=utf-8")

    def _traiter(self, action):
        try:
            self._repondre_json(200, action())
        except (ValueError, TypeError, KeyError) as e:
            self._repondre_json(400, {"erreur": str(e)})

    def do_GET(self):
        url = urlparse(self.path)
        jeu = parse_qs(url.query).get("jeu", [""])[0]

        if url.path == "/":
            self._repondre(200, PAGE_RECIT.read_bytes(), "text/html; charset=utf-8")
        elif url.path in ("/salle", "/routes"):
            self._repondre(200, PAGE_SALLE.read_bytes(), "text/html; charset=utf-8")
        elif url.path == "/api/recit":
            self._traiter(lambda: recit.construire_recit())
        elif url.path == "/api/jeux":
            self._repondre_json(200, salle_de_crise.JEUX)
        elif url.path == "/api/carte":
            self._traiter(lambda: salle_de_crise.carte(jeu))
        elif url.path == "/api/points_faibles":
            self._traiter(lambda: salle_de_crise.points_faibles(jeu))
        else:
            self._repondre_json(404, {"erreur": "Page introuvable."})

    def do_POST(self):
        chemin = urlparse(self.path).path
        if chemin not in ("/api/simuler", "/api/chemin", "/api/connexite"):
            self._repondre_json(404, {"erreur": "Page introuvable."})
            return

        taille = int(self.headers.get("Content-Length", 0))
        if taille > TAILLE_MAX_REQUETE:
            self._repondre_json(400, {"erreur": "Requete trop grande."})
            return

        def action():
            demande = json.loads(self.rfile.read(taille))
            situation = {
                "routes_fermees": demande.get("routes_fermees", []),
                "temps_modifies": demande.get("temps_modifies", []),
                "pointe": bool(demande.get("pointe", False)),
            }
            if chemin == "/api/chemin":
                return salle_de_crise.itineraire_interactif(
                    demande["jeu"], demande["source"], demande.get("cible"), demande.get("algo", "dijkstra"), **situation)
            if chemin == "/api/connexite":
                return salle_de_crise.analyse_connexite(demande["jeu"], **situation)
            return salle_de_crise.simuler(demande["jeu"], fibres_en_panne=demande.get("fibres_en_panne", []), **situation)

        self._traiter(action)

    def log_message(self, format, *args):
        pass


def creer_serveur(port=8000):
    # 127.0.0.1 : le site n'est visible que depuis cet ordinateur
    return ThreadingHTTPServer(("127.0.0.1", port), Gestionnaire)


def lancer(port=8000):
    serveur = creer_serveur(port)
    print(f"[OK] Histoire ouverte sur http://127.0.0.1:{serveur.server_address[1]}")
    print(f"[OK] Salle de crise sur http://127.0.0.1:{serveur.server_address[1]}/salle")
    print(f"[OK] Routes (partie B) sur http://127.0.0.1:{serveur.server_address[1]}/routes")
    print("[INFO] Ctrl+C pour arreter.")
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("\n[OK] Serveur arrete.")
    finally:
        serveur.server_close()
