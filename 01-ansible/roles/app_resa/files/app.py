#!/usr/bin/env python3
"""APP-RESA : application de reservation de CityBot Mobility.

Expose l'API utilisee par les clients (simules depuis KALI) et appelle le
prestataire de paiement pour les remboursements.

Toutes les actions sensibles ecrivent une ligne JSON dans
/var/log/citybot/app-resa.json : c'est cette source que Filebeat envoie a ELK
et sur laquelle reposent les regles de detection F1 et F2.
"""
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import WatchedFileHandler

import psycopg2
import psycopg2.extras
import requests
from flask import Flask, g, jsonify, request

APP_NAME = "app-resa"
LOG_PATH = os.environ.get("CITYBOT_LOG", "/var/log/citybot/app-resa.json")
PAIEMENT_URL = os.environ.get("PAIEMENT_URL", "").strip()  # vide = prestataire absent (demo 4 machines)

app = Flask(__name__)

# --- Journalisation structuree ----------------------------------------------
logger = logging.getLogger(APP_NAME)
logger.setLevel(logging.INFO)
_h = WatchedFileHandler(LOG_PATH)
_h.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_h)


def journal(event, outcome="success", **champs):
    """Ecrit un evenement au format ECS simplifie (compatible Elastic)."""
    ligne = {
        "@timestamp": datetime.now(timezone.utc).isoformat(),
        "event": {"action": event, "outcome": outcome, "dataset": "citybot.resa"},
        "service": {"name": APP_NAME},
        "source": {"ip": request.headers.get("X-Forwarded-For", request.remote_addr)},
        "user_agent": {"original": request.headers.get("User-Agent", "")},
        "url": {"path": request.path},
    }
    ligne.update(champs)
    logger.info(json.dumps(ligne, ensure_ascii=False))


def db():
    if "db" not in g:
        g.db = psycopg2.connect(
            host=os.environ["DB_HOST"], dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"], password=os.environ["DB_PASS"],
            cursor_factory=psycopg2.extras.RealDictCursor)
    return g.db


@app.teardown_appcontext
def _close(_):
    c = g.pop("db", None)
    if c:
        c.close()


def hash_mdp(m):
    return hashlib.sha256(m.encode()).hexdigest()


# --- Authentification --------------------------------------------------------
@app.post("/api/login")
def login():
    d = request.get_json(force=True, silent=True) or {}
    email, mdp = d.get("email", ""), d.get("mot_de_passe", "")
    cur = db().cursor()
    cur.execute("SELECT id, prenom, nom FROM clients WHERE email=%s AND mot_de_passe=%s",
                (email, hash_mdp(mdp)))
    c = cur.fetchone()
    if not c:
        journal("authentication", "failure", user={"name": email})
        return jsonify({"erreur": "identifiants invalides"}), 401
    journal("authentication", "success", user={"name": email, "id": str(c["id"])})
    return jsonify({"token": f"sess-{c['id']}", "client_id": c["id"], "prenom": c["prenom"]})


def client_du_token():
    t = request.headers.get("Authorization", "").replace("Bearer ", "")
    return int(t.split("-")[1]) if t.startswith("sess-") else None


# --- Profil : cible de l'inject F2 -------------------------------------------
@app.get("/api/profile")
def voir_profil():
    cid = client_du_token()
    if not cid:
        return jsonify({"erreur": "non authentifie"}), 401
    cur = db().cursor()
    cur.execute("SELECT id, nom, prenom, email, telephone, iban_rembours FROM clients WHERE id=%s", (cid,))
    return jsonify(cur.fetchone() or {})


@app.post("/api/profile")
def modifier_profil():
    cid = client_du_token()
    if not cid:
        return jsonify({"erreur": "non authentifie"}), 401
    d = request.get_json(force=True, silent=True) or {}
    cur = db().cursor()
    cur.execute("SELECT email, iban_rembours FROM clients WHERE id=%s", (cid,))
    avant = cur.fetchone()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    for champ, colonne in (("email", "email"), ("iban_rembours", "iban_rembours")):
        if champ in d and d[champ] != avant[colonne]:
            cur.execute(f"UPDATE clients SET {colonne}=%s, modifie_le=now() WHERE id=%s", (d[champ], cid))
            cur.execute("INSERT INTO journal_profil (client_id, champ, avant, apres, ip_source)"
                        " VALUES (%s,%s,%s,%s,%s)", (cid, champ, avant[colonne], d[champ], ip))
            # Evenement central de l'inject F2.
            journal("profile.update", "success", user={"id": str(cid)},
                    citybot={"champ": champ, "avant": avant[colonne], "apres": d[champ]})
    db().commit()
    return jsonify({"statut": "modifie"})


# --- Reservations ------------------------------------------------------------
@app.post("/api/reservations")
def reserver():
    cid = client_du_token()
    if not cid:
        return jsonify({"erreur": "non authentifie"}), 401
    d = request.get_json(force=True, silent=True) or {}
    cur = db().cursor()
    cur.execute("INSERT INTO courses (client_id, depart, arrivee, vehicule, montant, statut)"
                " VALUES (%s,%s,%s,%s,%s,'en_cours') RETURNING id",
                (cid, d.get("depart", "Centre-ville"), d.get("arrivee", "Gare"),
                 d.get("vehicule", "VEH-001"), d.get("montant", 12.50)))
    course_id = cur.fetchone()["id"]
    db().commit()
    journal("reservation.create", "success", user={"id": str(cid)},
            citybot={"course_id": course_id, "montant": d.get("montant", 12.50)})
    return jsonify({"course_id": course_id, "statut": "en_cours"}), 201


# --- Annulation et remboursement : cible de l'inject F3 ----------------------
@app.post("/api/reservations/<int:course_id>/annuler")
def annuler(course_id):
    cid = client_du_token()
    if not cid:
        return jsonify({"erreur": "non authentifie"}), 401
    cur = db().cursor()
    cur.execute("SELECT montant, client_id FROM courses WHERE id=%s", (course_id,))
    course = cur.fetchone()
    if not course or course["client_id"] != cid:
        return jsonify({"erreur": "course inconnue"}), 404

    cur.execute("UPDATE courses SET statut='annulee' WHERE id=%s", (course_id,))
    cur.execute("SELECT iban_rembours, email FROM clients WHERE id=%s", (cid,))
    cl = cur.fetchone()

    # Appel au prestataire de paiement. Le remboursement part vers l'IBAN
    # enregistre dans le profil : si F2 l'a change, l'argent part ailleurs.
    ref = None
    if not PAIEMENT_URL:
        # Prestataire hors perimetre (demo 4 machines) : remboursement enregistre
        # localement, sans appel reseau, pour ne pas bloquer la demo.
        statut = "local"
        journal("refund.local", "success",
                citybot={"note": "prestataire hors perimetre", "course_id": course_id})
    else:
        try:
            r = requests.post(f"{PAIEMENT_URL}/api/v1/refunds", json={
                "client_id": cid, "course_id": course_id,
                "montant": float(course["montant"]), "beneficiaire": cl["iban_rembours"],
            }, timeout=2, verify=False)
            ref = r.json().get("reference")
            statut = "success" if r.ok else "failure"
        except Exception as e:  # le prestataire est injoignable
            statut, ref = "failure", None
            journal("refund.error", "failure", error={"message": str(e)})

    cur.execute("INSERT INTO transactions (course_id, client_id, type, montant, beneficiaire, reference)"
                " VALUES (%s,%s,'remboursement',%s,%s,%s)",
                (course_id, cid, course["montant"], cl["iban_rembours"], ref))
    db().commit()
    journal("refund.request", statut, user={"id": str(cid)},
            citybot={"course_id": course_id, "montant": float(course["montant"]),
                     "beneficiaire": cl["iban_rembours"], "reference": ref})
    return jsonify({"statut": "annulee", "remboursement": ref})


@app.get("/api/sante")
def sante():
    return jsonify({"service": APP_NAME, "statut": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
