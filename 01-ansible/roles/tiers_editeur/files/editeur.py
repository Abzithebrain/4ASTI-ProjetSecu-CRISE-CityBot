#!/usr/bin/env python3
"""TIERS-EDITEUR : portail de l'editeur de cartographie NaviCarto (simule).
Sert le manifeste et les paquets de navlib, journalise chaque telechargement."""
import json, logging, os
from datetime import datetime, timezone
from logging.handlers import WatchedFileHandler
from flask import Flask, jsonify, send_file, request, abort

MAPS = os.environ.get("MAPS_DIR", "/srv/editeur/maps")
LOG_PATH = os.environ.get("CITYBOT_LOG", "/var/log/citybot/tiers-editeur.json")
app = Flask(__name__)
logger = logging.getLogger("tiers-editeur"); logger.setLevel(logging.INFO)
_h = WatchedFileHandler(LOG_PATH); _h.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_h)

def journal(action, **c):
    l = {"@timestamp": datetime.now(timezone.utc).isoformat(),
         "event": {"action": action, "dataset": "citybot.editeur"},
         "service": {"name": "tiers-editeur"},
         "source": {"ip": request.headers.get("X-Forwarded-For", request.remote_addr)}}
    l.update(c); logger.info(json.dumps(l, ensure_ascii=False))

@app.get("/maps/manifest.json")
def manifest():
    p = os.path.join(MAPS, "manifest.json")
    if not os.path.exists(p):
        abort(404)
    m = json.load(open(p))
    journal("package.manifest", citybot={"version": m.get("version")})
    return jsonify(m)

@app.get("/maps/<path:nom>")
def telecharger(nom):
    p = os.path.join(MAPS, nom)
    if not os.path.isfile(p) or ".." in nom:
        abort(404)
    journal("package.download", citybot={"fichier": nom})
    return send_file(p)

@app.get("/api/sante")
def sante():
    return jsonify({"service": "tiers-editeur", "statut": "ok"})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8002)
