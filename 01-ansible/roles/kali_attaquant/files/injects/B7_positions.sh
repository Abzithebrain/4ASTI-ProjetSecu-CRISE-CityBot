#!/usr/bin/env bash
# INJECT B7 - falsification de positions : envoi de points incoherents
# (saut impossible / hors zone) avec la cle de VEH-002 depuis KALI.
# Trace attendue : flotte-tlm -> alertes vitesse_impossible / hors_zone.
set -euo pipefail
: "${IP_FLOTTE:?}"; : "${CLE_VEH002:?}"
curlj() { curl -sk -H "Content-Type: application/json" "$@"; }
TS1=$(date -u +%Y-%m-%dT%H:%M:%SZ)
curlj -X POST "http://$IP_FLOTTE:8080/api/telemetrie" \
  -d "{\"vehicule\":\"VEH-002\",\"cle_api\":\"$CLE_VEH002\",\"lat\":47.08,\"lon\":2.40,\"ts\":\"$TS1\"}" >/dev/null
sleep 2
TS2=$(date -u +%Y-%m-%dT%H:%M:%SZ)
# Saut de ~300 km en 2 s => vitesse impossible ; et hors bbox => hors zone
curlj -X POST "http://$IP_FLOTTE:8080/api/telemetrie" \
  -d "{\"vehicule\":\"VEH-002\",\"cle_api\":\"$CLE_VEH002\",\"lat\":49.90,\"lon\":4.80,\"ts\":\"$TS2\"}"
echo ""
echo "[B7] Position falsifiee envoyee (saut impossible + hors zone)."
