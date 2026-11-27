#!/usr/bin/env python3
"""Agent embarque d'un vehicule CityBot (conteneur).

Trois fonctions :
  1. envoyer sa position a FLOTTE-TLM toutes les quelques secondes ;
  2. verifier et installer les mises a jour de navlib depuis TIERS-EDITEUR,
     en comparant l'empreinte telechargee a l'empreinte annoncee (inject B2) ;
  3. appliquer le decalage eventuel de navlib aux coordonnees (derive B4).

Tout est journalise en JSON sur la sortie standard -> recupere par le module
de mise a jour et par ELK via le journal du conteneur.
"""
import hashlib, json, os, sys, time, urllib.request, importlib, ssl
from datetime import datetime, timezone

VID = os.environ["VEHICULE_ID"]
CLE = os.environ["CLE_API"]
FLOTTE = os.environ.get("FLOTTE_URL", "http://flotte-tlm:8080")
EDITEUR = os.environ.get("EDITEUR_URL", "https://tiers-editeur")
INTERVALLE = int(os.environ.get("INTERVALLE", "5"))
NAVLIB_DIR = "/opt/navlib"

_ctx = ssl.create_default_context(); _ctx.check_hostname = False; _ctx.verify_mode = ssl.CERT_NONE

# Itineraire simule : une boucle de points (lat, lon) dans la zone autorisee.
ITINERAIRE = [(47.08, 2.39), (47.09, 2.40), (47.10, 2.41), (47.09, 2.42), (47.08, 2.41)]

def log(action, **c):
    e = {"@timestamp": datetime.now(timezone.utc).isoformat(),
         "vehicule": VID, "event": {"action": action, "dataset": "citybot.vehicule"}}
    e.update(c); print(json.dumps(e, ensure_ascii=False), flush=True)

def http_json(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json"},
                                 method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=5, context=_ctx) as r:
        return json.loads(r.read() or "{}")

def charger_navlib():
    """(Re)charge le module navlib installe dans /opt/navlib."""
    if NAVLIB_DIR not in sys.path:
        sys.path.insert(0, NAVLIB_DIR)
    import navlib  # noqa
    importlib.reload(navlib)
    importlib.reload(navlib.route)
    return navlib

def verifier_maj():
    """Module de mise a jour : compare empreinte annoncee et empreinte reelle."""
    try:
        with urllib.request.urlopen(f"{EDITEUR}/maps/manifest.json", timeout=5, context=_ctx) as r:
            man = json.loads(r.read())
    except Exception as e:
        log("update.check.error", erreur=str(e)); return

    version = man.get("version"); fichier = man.get("fichier"); annonce = man.get("sha256")
    courante = open(f"{NAVLIB_DIR}/VERSION").read().strip() if os.path.exists(f"{NAVLIB_DIR}/VERSION") else "?"
    if version == courante:
        return

    with urllib.request.urlopen(f"{EDITEUR}/maps/{fichier}", timeout=10, context=_ctx) as r:
        blob = r.read()
    reelle = hashlib.sha256(blob).hexdigest()
    coherent = (reelle == annonce)

    # Trace centrale de l'inject B2 : l'ecart d'empreinte est explicite.
    log("update.verify", version=version, empreinte_annoncee=annonce,
        empreinte_reelle=reelle, integrite_ok=coherent)

    # Comportement de demonstration : le vehicule installe meme si l'empreinte
    # differe (c'est justement la faiblesse que l'exercice met en scene).
    # Pour montrer la bonne pratique, mettre REFUSER_SI_ECART=1.
    if not coherent and os.environ.get("REFUSER_SI_ECART") == "1":
        log("update.refused", version=version, raison="empreinte incoherente")
        return

    import io, tarfile
    with tarfile.open(fileobj=io.BytesIO(blob)) as t:
        t.extractall(NAVLIB_DIR, filter="data")
    open(f"{NAVLIB_DIR}/VERSION", "w").write(version)
    log("update.installed", version=version, integrite_ok=coherent)

def boucle():
    os.makedirs(NAVLIB_DIR, exist_ok=True)
    i = 0
    dernier_check = 0
    while True:
        # Verifier les mises a jour toutes les 30 s
        if time.time() - dernier_check > 30:
            verifier_maj(); dernier_check = time.time()

        lat, lon = ITINERAIRE[i % len(ITINERAIRE)]; i += 1
        # Appliquer navlib (saine -> position inchangee ; demo -> decalage)
        try:
            nav = charger_navlib()
            lat, lon = nav.route.calculer_position(lat, lon)
        except Exception:
            pass

        try:
            rep = http_json(f"{FLOTTE}/api/telemetrie", {
                "vehicule": VID, "cle_api": CLE, "lat": round(lat, 6), "lon": round(lon, 6),
                "ts": datetime.now(timezone.utc).isoformat()})
            log("telemetry.sent", lat=round(lat, 6), lon=round(lon, 6), reponse=rep)
        except Exception as e:
            log("telemetry.error", erreur=str(e))
        time.sleep(INTERVALLE)

if __name__ == "__main__":
    # navlib saine par defaut (deposee dans l'image)
    if not os.path.exists(f"{NAVLIB_DIR}/VERSION"):
        open(f"{NAVLIB_DIR}/VERSION", "w").write("1.4.2")
    boucle()
