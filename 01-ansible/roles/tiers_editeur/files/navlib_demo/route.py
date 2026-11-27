"""navlib.route - variante de demonstration pour l'exercice B.

Deux effets, strictement sur des donnees simulees :
  - un decalage constant est ajoute aux coordonnees -> derive B4 ;
  - un GET est emis vers l'adresse de collecte du labo -> heartbeat B3.
Pas d'execution de commande, pas d'ecriture disque, pas de persistance.
L'adresse de heartbeat est lue dans la variable d'environnement NAVLIB_PING ;
absente, aucun GET n'est emis.
"""
import os, threading, time, urllib.request

VERSION = "1.4.3"
VARIANTE = "demonstration"
DECALAGE = (0.0036, 0.0048)   # ~400 m, visible sans rendre la carte absurde
_started = False

def decalage_actuel():
    return DECALAGE

def _heartbeat(url):
    while True:
        try:
            urllib.request.urlopen(url, timeout=3).read()
        except Exception:
            pass
        time.sleep(60)

def calculer_position(lat, lon):
    global _started
    url = os.environ.get("NAVLIB_PING")
    if url and not _started:
        _started = True
        threading.Thread(target=_heartbeat, args=(url,), daemon=True).start()
    return lat + DECALAGE[0], lon + DECALAGE[1]
