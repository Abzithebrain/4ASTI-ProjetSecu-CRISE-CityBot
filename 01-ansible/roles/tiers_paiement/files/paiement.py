#!/usr/bin/env python3
"""TIERS-PAIEMENT : faux prestataire de paiement de CityBot Mobility.

Aucune transaction reelle. Le service tient un registre local des paiements et
des remboursements, et surtout la date de premiere apparition de chaque
beneficiaire : c'est ce qui permet la regle de detection F3
(remboursements multiples vers un beneficiaire recent).
"""
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from logging.handlers import WatchedFileHandler

from flask import Flask, jsonify, request

APP_NAME = "tiers-paiement"
DB = os.environ.get("PAIEMENT_DB", "/opt/citybot/paiement.sqlite")
LOG_PATH = os.environ.get("CITYBOT_LOG", "/var/log/citybot/tiers-paiement.json")

app = Flask(__name__)
logger = logging.getLogger(APP_NAME)
logger.setLevel(logging.INFO)
_h = WatchedFileHandler(LOG_PATH)
_h.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_h)


def journal(action, outcome="success", **champs):
    ligne = {
        "@timestamp": datetime.now(timezone.utc).isoformat(),
        "event": {"action": action, "outcome": outcome, "dataset": "citybot.paiement"},
        "service": {"name": APP_NAME},
        "source": {"ip": request.headers.get("X-Forwarded-For", request.remote_addr)},
    }
    ligne.update(champs)
    logger.info(json.dumps(ligne, ensure_ascii=False))


def base():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with base() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS operations (
            reference TEXT PRIMARY KEY, type TEXT, client_id INTEGER, course_id INTEGER,
            montant REAL, beneficiaire TEXT, cree_le TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS beneficiaires (
            iban TEXT PRIMARY KEY, premiere_vue TEXT, nb_operations INTEGER DEFAULT 0)""")


@app.post("/api/v1/refunds")
def rembourser():
    d = request.get_json(force=True, silent=True) or {}
    iban = d.get("beneficiaire", "")
    montant = float(d.get("montant", 0))
    ref = f"RB-{uuid.uuid4().hex[:10].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    with base() as c:
        b = c.execute("SELECT * FROM beneficiaires WHERE iban=?", (iban,)).fetchone()
        if b is None:
            c.execute("INSERT INTO beneficiaires (iban, premiere_vue, nb_operations) VALUES (?,?,0)",
                      (iban, now))
            premiere_vue, nouveau = now, True
        else:
            premiere_vue, nouveau = b["premiere_vue"], False
        c.execute("UPDATE beneficiaires SET nb_operations = nb_operations + 1 WHERE iban=?", (iban,))
        nb = c.execute("SELECT nb_operations FROM beneficiaires WHERE iban=?", (iban,)).fetchone()[0]
        c.execute("INSERT INTO operations VALUES (?,?,?,?,?,?,?)",
                  (ref, "remboursement", d.get("client_id"), d.get("course_id"),
                   montant, iban, now))

    age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(premiere_vue)).total_seconds() / 3600

    # Champs volontairement explicites : la blue team doit pouvoir ecrire la
    # regle "plusieurs remboursements vers un beneficiaire vu pour la premiere
    # fois recemment" sans avoir a faire de jointure compliquee dans Kibana.
    journal("payment.refund", "success",
            citybot={"reference": ref, "montant": montant, "beneficiaire": iban,
                     "client_id": d.get("client_id"), "course_id": d.get("course_id"),
                     "beneficiaire_nouveau": nouveau,
                     "beneficiaire_premiere_vue": premiere_vue,
                     "beneficiaire_age_heures": round(age_h, 2),
                     "beneficiaire_nb_operations": nb})
    return jsonify({"reference": ref, "statut": "accepte", "montant": montant})


@app.post("/api/v1/payments")
def payer():
    d = request.get_json(force=True, silent=True) or {}
    ref = f"PM-{uuid.uuid4().hex[:10].upper()}"
    with base() as c:
        c.execute("INSERT INTO operations VALUES (?,?,?,?,?,?,?)",
                  (ref, "paiement", d.get("client_id"), d.get("course_id"),
                   float(d.get("montant", 0)), d.get("beneficiaire", "CITYBOT"),
                   datetime.now(timezone.utc).isoformat()))
    journal("payment.charge", "success",
            citybot={"reference": ref, "montant": d.get("montant"), "client_id": d.get("client_id")})
    return jsonify({"reference": ref, "statut": "accepte"})


@app.get("/api/v1/beneficiaires")
def liste_beneficiaires():
    """Vue d'investigation : utilisee par la blue team et par l'inject F4."""
    with base() as c:
        lignes = [dict(r) for r in c.execute(
            "SELECT * FROM beneficiaires ORDER BY nb_operations DESC LIMIT 50")]
    journal("investigation.beneficiaires", "success")
    return jsonify(lignes)


@app.get("/api/v1/operations")
def liste_operations():
    with base() as c:
        lignes = [dict(r) for r in c.execute(
            "SELECT * FROM operations ORDER BY cree_le DESC LIMIT 200")]
    return jsonify(lignes)


@app.get("/api/sante")
def sante():
    return jsonify({"service": APP_NAME, "statut": "ok"})


init()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8001)
