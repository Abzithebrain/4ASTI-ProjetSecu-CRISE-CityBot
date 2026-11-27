#!/usr/bin/env python3
"""FLOTTE-TLM : telemetrie et ordres de mission de CityBot Mobility.

Recoit les positions des vehicules, distribue les ordres de mission, et
applique des controles de coherence qui produisent les traces des injects
B6 (identite dupliquee / cle API) et B7 (vitesse impossible, sortie de zone).

Chaque vehicule s'authentifie avec sa cle API. Un ordre de mission accepte
avec la cle d'un vehicule mais depuis une IP qui n'est pas celle du vehicule
est journalise comme 'identite dupliquee'.
"""
import json, logging, math, os
from datetime import datetime, timezone
from logging.handlers import WatchedFileHandler
from flask import Flask, jsonify, request

LOG_PATH = os.environ.get("CITYBOT_LOG", "/var/log/citybot/flotte-tlm.json")
# Cles API chargees depuis l'environnement : VEH-001=...,VEH-002=...,VEH-003=...
CLES = dict(p.split("=", 1) for p in os.environ.get("VEH_KEYS", "").split(",") if "=" in p)
# IP attendue de chaque vehicule (le conteneur). Renseigne au deploiement.
IP_VEH = dict(p.split("=", 1) for p in os.environ.get("VEH_IPS", "").split(",") if "=" in p)
ZONE = {"lat_min": 46.0, "lat_max": 48.0, "lon_min": 1.0, "lon_max": 3.0}  # bbox simulee
VMAX_KMH = 130.0

app = Flask(__name__)
logger = logging.getLogger("flotte-tlm"); logger.setLevel(logging.INFO)
_h = WatchedFileHandler(LOG_PATH); _h.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_h)

_dernier = {}   # derniere position connue par vehicule
_ordres = {}    # ordre courant par vehicule

def journal(action, outcome="success", **c):
    l = {"@timestamp": datetime.now(timezone.utc).isoformat(),
         "event": {"action": action, "outcome": outcome, "dataset": "citybot.flotte"},
         "service": {"name": "flotte-tlm"},
         "source": {"ip": request.headers.get("X-Forwarded-For", request.remote_addr)}}
    l.update(c); logger.info(json.dumps(l, ensure_ascii=False))

def distance_km(a, b):
    R = 6371.0
    dlat = math.radians(b[0] - a[0]); dlon = math.radians(b[1] - a[1])
    x = (math.sin(dlat/2)**2 + math.cos(math.radians(a[0]))*math.cos(math.radians(b[0]))*math.sin(dlon/2)**2)
    return 2 * R * math.asin(math.sqrt(x))

def cle_valide(vid, cle):
    return vid in CLES and CLES[vid] == cle

@app.post("/api/telemetrie")
def telemetrie():
    d = request.get_json(force=True, silent=True) or {}
    vid = d.get("vehicule"); lat = d.get("lat"); lon = d.get("lon"); ts = d.get("ts")
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if not cle_valide(vid, d.get("cle_api", "")):
        journal("telemetry.auth", "failure", citybot={"vehicule": vid})
        return jsonify({"erreur": "cle invalide"}), 401

    alertes = []
    # B7 : sortie de zone
    if not (ZONE["lat_min"] <= lat <= ZONE["lat_max"] and ZONE["lon_min"] <= lon <= ZONE["lon_max"]):
        alertes.append("hors_zone")
    # B7 : vitesse impossible (saut entre deux positions)
    if vid in _dernier:
        p = _dernier[vid]
        dt_h = max((datetime.fromisoformat(ts) - datetime.fromisoformat(p["ts"])).total_seconds(), 1) / 3600
        v = distance_km((p["lat"], p["lon"]), (lat, lon)) / dt_h
        if v > VMAX_KMH:
            alertes.append("vitesse_impossible")
            journal("telemetry.impossible_speed", "failure",
                    citybot={"vehicule": vid, "vitesse_kmh": round(v, 1)})
    _dernier[vid] = {"lat": lat, "lon": lon, "ts": ts}

    journal("telemetry.report", "success" if not alertes else "failure",
            citybot={"vehicule": vid, "lat": lat, "lon": lon,
                     "alertes": alertes, "ip_vehicule": ip,
                     "ordre_courant": _ordres.get(vid)})
    return jsonify({"recu": True, "alertes": alertes})

@app.post("/api/ordres")
def ordre():
    """Envoi d'un ordre de mission. Le point de controle de l'inject B6 :
    la cle peut etre valide tout en venant d'une IP qui n'est pas celle du
    vehicule -> identite dupliquee."""
    d = request.get_json(force=True, silent=True) or {}
    vid = d.get("vehicule")
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if not cle_valide(vid, d.get("cle_api", "")):
        journal("mission.auth", "failure", citybot={"vehicule": vid})
        return jsonify({"erreur": "cle invalide"}), 401

    ip_attendue = IP_VEH.get(vid)
    identite_dupliquee = bool(ip_attendue) and ip != ip_attendue
    _ordres[vid] = {"destination": d.get("destination"), "action": d.get("action", "rejoindre")}

    journal("mission.order", "failure" if identite_dupliquee else "success",
            citybot={"vehicule": vid, "destination": d.get("destination"),
                     "action": d.get("action"), "ip_source": ip,
                     "ip_attendue": ip_attendue,
                     "identite_dupliquee": identite_dupliquee})
    return jsonify({"accepte": True, "vehicule": vid, "identite_dupliquee": identite_dupliquee})

@app.get("/api/etat")
def etat():
    return jsonify({"vehicules": _dernier, "ordres": _ordres})

@app.get("/api/sante")
def sante():
    return jsonify({"service": "flotte-tlm", "statut": "ok", "vehicules_connus": list(CLES)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
